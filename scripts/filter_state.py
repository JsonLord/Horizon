"""Optional read-only Actions cache persistence; never writes the intel archive."""
import argparse
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import zipfile

import httpx
from src.research.reporting import atomic,dumps

NAME='shared-filter-cache'
LIMIT=5_000_000

def seal(root):
    source=root/'state.sqlite'
    if not source.exists():return {'status':'no_state'}
    if source.is_symlink() or source.stat().st_size>LIMIT:raise ValueError('state_limit')
    with sqlite3.connect(source) as db,sqlite3.connect(root/'checkpoint.sqlite') as dest:db.backup(dest)
    atomic(root/'manifest.json',dumps({'schema_version':'1.0','source_sha':os.getenv('GITHUB_SHA','local'),'run_id':os.getenv('GITHUB_RUN_ID'),'sha256':hashlib.sha256((root/'checkpoint.sqlite').read_bytes()).hexdigest()}))
    return {'status':'sealed'}

def install(root,archive,source_sha):
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        names=[x.filename for x in z.infolist() if not x.is_dir()]
        if sorted(names)!=['checkpoint.sqlite','manifest.json'] or any(e.file_size>LIMIT for e in z.infolist()):raise ValueError('invalid_cache_members')
        manifest=json.loads(z.read('manifest.json'));blob=z.read('checkpoint.sqlite')
    if manifest.get('schema_version')!='1.0' or manifest.get('source_sha')!=source_sha or hashlib.sha256(blob).hexdigest()!=manifest['sha256']:raise ValueError('cache_binding_or_hash')
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        candidate=Path(tmp)/'validated.sqlite';candidate.write_bytes(blob)
        with sqlite3.connect('file:'+str(candidate.resolve())+'?mode=ro',uri=True) as db:
            if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('sqlite_integrity')
            if db.execute('SELECT count(*) FROM state').fetchone()[0]>100000:raise ValueError('cache_row_limit')
        candidate.replace(root/'state.sqlite')
    return {'status':'restored','previous_run_id':manifest['run_id']}

async def restore(root):
    repo=os.environ['GITHUB_REPOSITORY'];sha=os.environ['GITHUB_SHA']
    async with httpx.AsyncClient(timeout=30,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN']}) as client:
        async def get(path):
            r=await client.get('https://api.github.com/repos/'+repo+'/'+path)
            if r.status_code>=400:raise ValueError('cache_api_unavailable')
            if len(r.content)>2_000_000:raise ValueError('cache_metadata_limit')
            return r.json()
        runs=await get('actions/workflows/horizon-intel.yml/runs?status=success&per_page=20')
        for run in runs['workflow_runs']:
            if run['head_sha']!=sha or run['head_branch']!=os.environ['GITHUB_REF_NAME'] or run['path']!='.github/workflows/horizon-intel.yml':continue
            artifacts=await get('actions/runs/'+str(run['id'])+'/artifacts?per_page=100')
            for artifact in artifacts['artifacts']:
                if artifact['name']!=NAME or artifact['expired'] or artifact['size_in_bytes']>LIMIT:continue
                response=await client.get('https://api.github.com/repos/'+repo+'/actions/artifacts/'+str(artifact['id'])+'/zip',follow_redirects=True)
                if response.status_code>=400 or len(response.content)>LIMIT:raise ValueError('cache_download_unavailable')
                if artifact.get('digest') and artifact['digest']!='sha256:'+hashlib.sha256(response.content).hexdigest():raise ValueError('cache_zip_digest')
                return install(root,response.content,sha)
    return {'status':'cold_start'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['seal','restore']);p.add_argument('--root',type=Path,default=Path('data/research/filtering'));a=p.parse_args()
    try:print(json.dumps(seal(a.root) if a.command=='seal' else asyncio.run(restore(a.root))))
    except Exception:
        # Cache loss must not erase last-good research or leak signed URL exceptions.
        print('::warning title=Filtering cache unavailable::Continuing with validated current collection and deterministic/bounded inference; cache URL/body omitted.')
