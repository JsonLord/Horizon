"""Data-only draft PR transport, with owned-branch CAS and idempotent updates."""
import hashlib
import re
import os
from urllib.parse import quote

MARKER = '<!-- horizon-funding-data-review:v1 -->'


def blob_sha(content):
    raw=content.encode()
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


async def publish_review(api, *, files, base_ref, base_sha, branch, title, body, qualification=False, complete_data_tree=False):
    # Production callers enforce main-workflow policy before reaching this helper.
    from scripts.funding_research import allowed_path
    if base_ref=='main':
        from scripts.funding_research import policy
        if qualification or not policy().review_pr_enabled or os.getenv('GITHUB_REF')!='refs/heads/main' or not os.getenv('GITHUB_WORKFLOW_REF','').endswith('/.github/workflows/funding-research.yml@refs/heads/main') or base_sha!=os.getenv('GITHUB_SHA'):
            raise PermissionError('Production funding review remains disabled outside reviewed main workflow')
    elif not qualification:
        raise PermissionError('Sandbox publication requires explicit qualification mode')
    sandbox=re.fullmatch(r'automation/funding-acceptance-base-([a-f0-9]{12})',base_ref)
    if not (base_ref=='main' and branch=='automation/funding-research') and not (sandbox and branch=='automation/funding-acceptance-review-'+sandbox[1]):
        raise PermissionError('Only funding production or isolated acceptance refs are allowed')
    if not re.fullmatch(r'[a-f0-9]{40}',base_sha) or any(not allowed_path(p) or (v is not None and len(v.encode())>1_000_000) for p,v in files.items()):
        raise ValueError('Unapproved generated path, source SHA or size')
    if not files:return {'status':'no_change','writes':0}
    base=await api.call('GET','commits/'+quote(base_ref,safe=''))
    if base['sha']!=base_sha:raise ValueError('Base advanced; recollect before proposing')
    opened=await api.call('GET','pulls?state=open&base='+quote(base_ref,safe='')+'&per_page=100')
    legacy=[p for p in opened if base_ref=='main' and p.get('head',{}).get('ref','').startswith('automation/funding-research-')]
    if legacy:return {'status':'pending_review','writes':0,'migration_required':True,'url':legacy[0]['html_url']}
    matching=[p for p in opened if p.get('head',{}).get('ref')==branch]
    if len(matching)>1:raise ValueError('Duplicate review PRs; reconcile before writing')
    pr=matching[0] if matching else None
    if pr and (MARKER not in (pr.get('body') or '') or pr.get('head',{}).get('repo',{}).get('full_name')!=api.repository):
        raise PermissionError('Refusing to adopt an unowned review PR')
    head=await api.call('GET','git/ref/heads/'+branch,missing=True)
    if head and not pr:raise ValueError('Unassociated existing branch; reconcile without overwrite')
    parent=head['object']['sha'] if head else base_sha
    commit=await api.call('GET','commits/'+parent) if head else base
    if head:
        comparison=await api.call('GET','compare/'+base_sha+'...'+parent)
        if len(comparison.get('files',[]))>=300 or any(not allowed_path(f['filename']) or f.get('previous_filename') and not allowed_path(f['previous_filename']) for f in comparison.get('files',[])):
            raise PermissionError('Existing branch contains changes outside the generated-data boundary')
    tree=await api.call('GET','git/trees/'+commit['commit']['tree']['sha']+'?recursive=1')
    if tree.get('truncated'):raise ValueError('Incomplete Git tree; cannot compare safely')
    entries={e['path']:e for e in tree['tree'] if e['type']=='blob'}
    if complete_data_tree:
        files=dict(files)
        files.update({p:None for p in entries if allowed_path(p) and p not in files})
    changes={p:v for p,v in files.items() if (v is None and p in entries) or (v is not None and (p not in entries or entries[p]['sha']!=blob_sha(v) or entries[p]['mode']!='100644'))}
    if not changes:return {'status':'pending_review' if pr else 'no_change','writes':0,'reused':bool(pr),'url':pr['html_url'] if pr else None}
    objects=[]
    for path,content in sorted(changes.items()):
        sha=None
        if content is not None:sha=(await api.call('POST','git/blobs',{'content':content,'encoding':'utf-8'}))['sha']
        objects.append({'path':path,'mode':'100644','type':'blob','sha':sha})
    rendered=await api.call('POST','git/trees',{'base_tree':commit['commit']['tree']['sha'],'tree':objects})
    new=await api.call('POST','git/commits',{'message':'Review funding research data','parents':[parent],'tree':rendered['sha']})
    if (await api.call('GET','commits/'+quote(base_ref,safe='')))['sha']!=base_sha:raise ValueError('Base advanced; no ref changed')
    if head:
        if (await api.call('GET','git/ref/heads/'+branch))['object']['sha']!=parent:raise ValueError('Review branch advanced; no overwrite')
        await api.call('PATCH','git/refs/heads/'+branch,{'sha':new['sha'],'force':False})
        result=await api.call('PATCH','pulls/'+str(pr['number']),{'body':MARKER+'\n\n'+body})
    else:
        await api.call('POST','git/refs',{'ref':'refs/heads/'+branch,'sha':new['sha']})
        result=await api.call('POST','pulls',{'head':branch,'base':base_ref,'title':title,'body':MARKER+'\n\n'+body,'draft':True})
    return {'status':'pending_review','reused':bool(pr),'url':result['html_url'],'paths':sorted(changes),'head_sha':new['sha']}
