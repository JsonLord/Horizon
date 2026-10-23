"""Independent-run funding qualification. Read-only GitHub token, local artifacts only."""
import asyncio
import base64
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile
import zlib

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit
from src.research.profiles import safe_url
import httpx

from scripts.qualify_funding import snapshot, verify_folders
from scripts.funding_research import allowed_path
from src.research.funding.models import Opportunity
from src.research.profiles import ROOT
from src.research.programs.fetch import ProgramFetcher
from src.research.programs.model_contract import inspect_contract
from src.research.programs.laya import classify
from src.research.programs.relevance import load_policy, score
from src.research.programs.models import Program, Evidence, Fact
from src.research.publisher import validate
from src.research.reporting import Archive, atomic, dumps
from src.research.service import ResearchService

NAME = 'funding-acceptance-snapshot'
BRANCH = 'feature/program-intelligence-implementation'


def notice(title, value):
    encoded = base64.b64encode(zlib.compress(dumps(value).encode())).decode()
    parts = [encoded[i:i+2800] for i in range(0, len(encoded), 2800)]
    if len(parts) > 30:
        raise ValueError('Public proof exceeds bounded annotation budget')
    for i, part in enumerate(parts):
        print(f'::notice title={title}-{i+1}-of-{len(parts)}::{part}')


def snapshot_path(name):
    p = PurePosixPath(name)
    return not p.is_absolute() and '..' not in p.parts and '\\' not in name and (name.startswith('intel/') and p.suffix in {'.json', '.md', '.jsonl'} or allowed_path(name) and name.startswith('research/') or name in {'research/funding-de-eu/NOMINATION_REVIEWS.json','research/funding-de-eu/NOMINATION_REVIEWS.md'})


def seal(root, source_sha, run_id):
    files = snapshot(root)
    if any(not snapshot_path(p) for p in files) or sum((root/p).stat().st_size for p in files) > 4_000_000:
        raise ValueError('Snapshot escaped bounded public data paths')
    manifest = {'schema_version':'1.0','source_sha':source_sha,'workflow_run_id':run_id,'files':files}
    atomic(root/'snapshot.json', dumps(manifest))
    return hashlib.sha256(dumps(manifest).encode()).hexdigest()


def verify_snapshot(root, source_sha, run_id):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Snapshot symlink')
    manifest = json.loads((root/'snapshot.json').read_text())
    if manifest.get('schema_version')!='1.0' or manifest['source_sha']!=source_sha or str(manifest['workflow_run_id'])!=str(run_id):
        raise ValueError('Snapshot source/run binding mismatch')
    actual = snapshot(root); actual.pop('snapshot.json',None)
    if actual != manifest['files'] or any(not snapshot_path(p) for p in actual):
        raise ValueError('Snapshot path or checksum mismatch')
    validate(root)
    with tempfile.TemporaryDirectory() as temp:
        clone=Path(temp)/'state';shutil.copytree(root,clone)
        verify_folders(clone)
    return manifest


async def restore_previous(root, previous, source_sha, client):
    if not re.fullmatch(r'[0-9]{1,20}',previous):raise ValueError('Invalid previous run ID')
    repo=os.environ['GITHUB_REPOSITORY']
    async def get(path):
        try:response=await client.get(f'https://api.github.com/repos/{repo}/{path}')
        except httpx.HTTPError:raise RuntimeError('Snapshot metadata transport unavailable') from None
        if response.status_code>=400:raise RuntimeError('Snapshot metadata retrieval failed HTTP '+str(response.status_code))
        return response.json()
    run=await get('actions/runs/'+previous)
    if run['head_sha']!=source_sha or run['head_branch']!=BRANCH or run['event']!='workflow_dispatch' or run['path']!='.github/workflows/horizon-intel.yml' or run['status']!='completed' or run['conclusion']!='success':
        raise ValueError('Prior run is not a successful same-revision qualification')
    artifacts=(await get('actions/runs/'+previous+'/artifacts?per_page=100'))['artifacts']
    choices=[a for a in artifacts if a['name']==NAME and not a['expired']]
    if len(choices)!=1:raise ValueError('Need exactly one live funding snapshot artifact')
    artifact=choices[0]
    try:response=await client.get(f'https://api.github.com/repos/{repo}/actions/artifacts/{artifact["id"]}/zip',follow_redirects=True)
    except httpx.HTTPError:raise RuntimeError('Snapshot artifact transport unavailable; URL and response omitted') from None
    if response.status_code>=400:raise RuntimeError('Snapshot artifact download failed HTTP '+str(response.status_code)+'; URL and response omitted')
    if len(response.content)>8_000_000:raise ValueError('Oversized snapshot ZIP')
    digest=hashlib.sha256(response.content).hexdigest()
    if artifact.get('digest') and artifact['digest']!='sha256:'+digest:raise ValueError('Artifact ZIP digest mismatch')
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names=set()
        for entry in archive.infolist():
            if entry.is_dir():continue
            if entry.filename in names or entry.file_size>1_000_000 or stat.S_ISLNK(entry.external_attr>>16) or (entry.filename!='snapshot.json' and not snapshot_path(entry.filename)):
                raise ValueError('Unsafe snapshot ZIP entry')
            names.add(entry.filename)
        if sum(e.file_size for e in archive.infolist())>4_000_000:raise ValueError('Oversized expanded snapshot')
        for entry in archive.infolist():
            if not entry.is_dir():
                path=root/entry.filename;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(entry))
    manifest=verify_snapshot(root,source_sha,previous)
    return {'previous_run_id':previous,'artifact_id':artifact['id'],'artifact_name':NAME,'zip_sha256':digest,'manifest_sha256':hashlib.sha256(dumps(manifest).encode()).hexdigest()}


def records(root):
    return {r.opportunity_id:r for p in (root/'research/funding-de-eu').glob('opportunities/*/opportunity.json') if (r:=Opportunity.model_validate_json(p.read_text()))}


def recovery_check(root, work):
    # Simulate interrupted working-tree writes; recover only from the sealed checkpoint.
    interrupted=work/'interrupted';shutil.copytree(root,interrupted)
    (interrupted/'intel/manifest.json').write_text('{interrupted')
    try:verify_snapshot(interrupted,os.environ['GITHUB_SHA'],os.environ['GITHUB_RUN_ID'])
    except (ValueError,KeyError):pass
    else:raise ValueError('Interrupted snapshot was accepted')
    shutil.rmtree(interrupted);shutil.copytree(root,interrupted)
    verify_snapshot(interrupted,os.environ['GITHUB_SHA'],os.environ['GITHUB_RUN_ID'])
    return {'simulated_partial_write_rejected':True,'sealed_checkpoint_restored':True,'exact_tree_restored':snapshot(root)==snapshot(interrupted),'scope':'partial working-tree write; not process-kill atomicity'}


async def observations():
    sources=json.loads((ROOT/'config/funding-sources.json').read_text())['sources']
    fetcher=ProgramFetcher(max_pages=10)
    output=[]
    for source in sources:
        page=await fetcher.fetch(source['url'],datetime.now(UTC).isoformat())
        item={'opportunity_id':source['opportunity_id'],'url':page.final_url,'observed_at':page.observed_at,'error':page.error,'sha256':page.fingerprint if not page.error else None,'excerpts':[]}
        if not page.error:
            soup=BeautifulSoup(page.html,'html.parser')
            for n in soup(['script','style','nav','footer']):n.decompose()
            text=' '.join(soup.get_text(' ',strip=True).split())
            old=records(ROOT)[source['opportunity_id']]
            item['prior_program_sha256']=next(r.content_sha256 for r in old.resources if r.resource_id=='program')
            item['raw_page_changed']=item['sha256']!=item['prior_program_sha256']
            item['old_quote_checks']={r.resource_id:bool(r.quotation and ' '.join(r.quotation.split()) in text) for r in old.resources if r.verified and r.url==source['url']}
            for pattern in ['Ab sofort','Wer wird','Gründung','Antrag','Natural persons','Short proposals','If your short proposal','Proposals will be batched','Applicants from EU','Grant funding','TRL']:
                match=re.search(re.escape(pattern),text,re.I)
                if match:item['excerpts'].append({'anchor':pattern,'quotation':text[match.start():match.start()+500]})
        output.append(item)
    return output


async def nomination_checks():
    queue=json.loads((ROOT/'research/funding-de-eu/RESEARCH_QUEUE.json').read_text())
    fetcher=ProgramFetcher(max_pages=4)
    results=[]
    for candidate in queue['candidates']:
        if candidate['origin']!='public_search':continue
        at=datetime.now(UTC).isoformat()
        page=await fetcher.fetch(candidate['url'],at)
        row={'candidate_id':candidate['candidate_id'],'observed_at':at,'url':page.final_url,'error':page.error,'outbound_links':[],'quotation':None,'sha256':page.fingerprint if not page.error else None}
        if not page.error:
            soup=BeautifulSoup(page.html,'html.parser')
            for n in soup(['script','style','nav','footer']):n.decompose()
            row['quotation']=' '.join(soup.get_text(' ',strip=True).split())[:500]
            for a in soup.find_all('a',href=True):
                try:url=safe_url(urljoin(page.final_url,a['href']))
                except ValueError:continue
                if urlsplit(url).hostname not in {'news.google.com','www.google.com','accounts.google.com','policies.google.com','support.google.com'} and url not in row['outbound_links']:
                    row['outbound_links'].append(url)
                    if len(row['outbound_links'])==8:break
        results.append(row)
    return results


async def model_check():
    contract=await inspect_contract();p=load_policy()
    # Public evidence fixture exercises live inference; never use applicant/private seed data.
    at=datetime.now(UTC).isoformat()
    # Use a real official program quotation from the committed evidence register.
    old=records(ROOT)['eu-eic-accelerator'];resource=next(x for x in old.resources if x.resource_id=='funding')
    # The model check is optional; schema issues become explicit failure evidence, not fake inference.
    from src.research.programs.verify import seed_record
    r=seed_record({'key':'acceptance-eic','name':'EIC Accelerator','url':resource.url,'official_domains':old.official_domains},at)
    eid=hashlib.sha256(resource.quotation.encode()).hexdigest()[:24]
    r.source_evidence=[Evidence(evidence_id=eid,url=resource.url,observed_at=resource.retrieved_at.isoformat(),quotation=resource.quotation,content_fingerprint=resource.content_sha256,location="official funding terms",primary=True)]
    r.funding_terms=old.claims['funding'].value
    r.facts={'funding_terms':Fact(value=old.claims['funding'].value,evidence_ids=[eid],last_verified=resource.retrieved_at.isoformat())}
    semantic,metadata=await classify(r,p,contract)
    return {'configured_model':p.laya.model,'configured_endpoint_matches_reviewed_native_contract':p.laya.inference_endpoint.endswith('/v1/system-one'),'contract_status':contract['status'],'inference':metadata,'fallback_score':score(r,p,semantic,metadata).model_dump(mode='json')}


async def main():
    if os.environ.get('GITHUB_REF')!='refs/heads/'+BRANCH or os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch':raise PermissionError('Read-only acceptance requires explicit implementation-branch dispatch')
    output=ROOT/'data/funding-acceptance';state=output/'snapshot'
    if output.exists():raise ValueError('Use a fresh hosted checkout')
    state.mkdir(parents=True)
    previous=os.getenv('PREVIOUS_RUN_ID','')
    restored=None
    if previous:
        async with httpx.AsyncClient(timeout=60,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'}) as client:
            restored=await restore_previous(state,previous,os.environ['GITHUB_SHA'],client)
    else:
        shutil.copytree(ROOT/'research/funding-de-eu',state/'research/funding-de-eu',dirs_exist_ok=True)
        for name in ('Funding DK (DE missing).md','RESEARCH_QUEUE.json','RESEARCH_UPDATES.md'):
            (state/'research/funding-de-eu'/name).unlink(missing_ok=True)
    before=records(state);histories={k:(state/'research/funding-de-eu/opportunities'/next(p.parent.name for p in (state/'research/funding-de-eu').glob('opportunities/*/opportunity.json') if json.loads(p.read_text())['opportunity_id']==k)/'change-history.jsonl').read_text() for k in before}
    previous_report=Archive(state).list('funding/de-eu')
    service=ResearchService(state);job=await service.submit({'profile_id':'funding/de-eu','depth':40},requested_by='github_actions');done=await service.wait(job['job_id'])
    if not done.get('report_id'):raise ValueError('No structured report')
    report=Archive(state).get(done['report_id']);validate(state)
    state_proof=verify_folders(state);after=records(state)
    preserved={}
    for key,old in before.items():
        fresh=after[key]
        if fresh.collection_error and fresh.claims!=old.claims:raise ValueError('Failed refresh replaced reviewed claims')
        folder=next(p.parent for p in (state/'research/funding-de-eu').glob('opportunities/*/opportunity.json') if json.loads(p.read_text())['opportunity_id']==key)
        events=[json.loads(line) for line in (folder/'change-history.jsonl').read_text().splitlines()]
        if not (folder/'change-history.jsonl').read_text().startswith(histories[key]) or len({e['record_sha256'] for e in events})!=len(events):raise ValueError('History prefix lost or duplicate event')
        preserved[key]={'claims_preserved':fresh.claims==old.claims,'deadline_preserved':fresh.deadline_token==old.deadline_token,'collection_error':fresh.collection_error,'history_count':len(events)}
    if previous_report and report['history'].get('previous_report_id')!=previous_report[0]['report_id']:raise ValueError('Prior report comparison not restored')
    # Remove old seal before creating a fresh, fully checksummed snapshot.
    (state/'snapshot.json').unlink(missing_ok=True)
    shutil.rmtree(state/'jobs',ignore_errors=True)
    (state/'research/.funding-de-eu.lock').unlink(missing_ok=True)
    manifest_sha=seal(state,os.environ['GITHUB_SHA'],os.environ['GITHUB_RUN_ID'])
    recovery=recovery_check(state,output)
    observation=await observations()
    nominations=await nomination_checks()
    try:model=await model_check()
    except Exception as exc:model={'status':'qualification_failed','error_class':type(exc).__name__,'fallback':'deterministic'}
    proof={'schema_version':'1.0','run_id':os.environ['GITHUB_RUN_ID'],'source_sha':os.environ['GITHUB_SHA'],'runner_instance':os.getenv('RUNNER_NAME'),'observed_at':datetime.now(UTC).isoformat(),'read_only':True,'restored':restored,'snapshot_manifest_sha256':manifest_sha,'snapshot_artifact_name':NAME,'report_id':done['report_id'],'report_status':report['status'],'comparison_report_id':report['history'].get('previous_report_id'),'state':state_proof,'records':preserved,'recovery':recovery,'reuse_policy':'Recheck every official source; reuse reviewed terms only with original provenance. Exact re-render is idempotent.','observations':observation,'nominations':nominations,'model':model}
    atomic(output/'proof.json',dumps(proof));notice('funding-acceptance-proof',proof)


if __name__=='__main__':asyncio.run(main())
