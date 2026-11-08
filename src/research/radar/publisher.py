"""GitHub-only data publisher; no branch code is executed, no force updates."""
import base64
import json
import os
from pathlib import Path
import httpx
from ..reporting import dumps
from .contracts import RADARS, Digest, utc
from .storage import allowed_path, validate_tree


class GitHubData:
    def __init__(self,repo='JsonLord/Horizon',token=None,client=None):
        if repo!='JsonLord/Horizon':raise ValueError('Unapproved repository')
        self.repo=repo
        self.client=client or httpx.Client(base_url='https://api.github.com',headers={'Authorization':'Bearer '+(token or os.getenv('GITHUB_TOKEN','')),'Accept':'application/vnd.github+json'},timeout=30,follow_redirects=False)
    def api(self,method,path,**kwargs):
        response=self.client.request(method,'/repos/'+self.repo+'/'+path,**kwargs)
        if response.status_code>=400:raise RuntimeError('GitHub HTTP '+str(response.status_code))
        return response.json()
    def read(self,radar,root):
        if radar not in RADARS:raise ValueError('Unknown radar')
        # Obtain ref once, pin all subsequent reads to that immutable commit.
        try:head=self.api('GET','git/ref/heads/radar/'+radar)['object']['sha']
        except RuntimeError as e:
            if str(e)=='GitHub HTTP 404':return None
            raise
        tree=self.api('GET','git/trees/'+head,params={'recursive':'1'})
        if tree.get('truncated'):raise ValueError('Truncated radar tree')
        total=0
        for entry in tree['tree']:
            if entry['type']=='tree':continue
            name=entry['path']
            if not allowed_path(name) or entry.get('mode')!='100644' or entry.get('size',0)>1_000_000:raise ValueError('Unsafe remote data tree')
            data=base64.b64decode(self.api('GET','git/blobs/'+entry['sha'])['content'])
            total+=len(data)
            if total>20_000_000:raise ValueError('Snapshot too large')
            dest=Path(root)/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        validate_tree(root,radar)
        return head
    def publish(self,radar,root):
        if radar not in RADARS:raise ValueError('Unknown radar branch')
        validate_tree(root,radar)
        # This routine supports data publication only after explicit deployment
        # enablement. Local branch initialization is a separate reviewed operation.
        from .pipeline import registry
        if not registry()['publication_enabled'] or os.getenv('GITHUB_REF')!='refs/heads/main' or not os.getenv('GITHUB_WORKFLOW_REF','').endswith('@refs/heads/main'):
            raise ValueError('Publication requires reviewed main code and explicit enablement')
        return self._publish_validated(radar,root)
    def _publish_validated(self,radar,root):
        import tempfile
        validate_tree(root,radar)
        for attempt in range(3):
            with tempfile.TemporaryDirectory() as temp:
                oldhead=self.read(radar,temp)
                if oldhead is None:raise ValueError('Radar branch must be initialized by operator review')
                files={p.relative_to(root).as_posix():p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}
                changes=[]
                for name,data in files.items():
                    old=Path(temp)/name
                    if old.exists() and old.read_bytes()==data:continue
                    if name.startswith(('weekly/','reports/')) and old.exists():raise ValueError('Immutable history conflict')
                    if name=='weekly-digest.json' and old.exists():
                        current=Digest.model_validate_json(old.read_text());incoming=Digest.model_validate_json(data)
                        if utc(incoming.week_end_utc)<utc(current.week_end_utc):raise ValueError('Latest week regression')
                    blob=self.api('POST','git/blobs',json={'content':base64.b64encode(data).decode(),'encoding':'base64'})
                    changes.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']})
                if not changes:return {'status':'unchanged','commit':oldhead,'writes':0}
                tree=self.api('POST','git/trees',json={'base_tree':oldhead,'tree':changes})
                commit=self.api('POST','git/commits',json={'message':'Publish validated '+radar+' research data','tree':tree['sha'],'parents':[oldhead]})
                try:
                    self.api('PATCH','git/refs/heads/radar/'+radar,json={'sha':commit['sha'],'force':False})
                    return {'status':'published','commit':commit['sha'],'writes':len(changes)}
                except RuntimeError as exc:
                    if str(exc) not in ('GitHub HTTP 409','GitHub HTTP 422') or attempt==2:raise
                    # Ref moved. Re-read and enforce history/latest invariants again.
        raise RuntimeError('Concurrent publication did not converge')
