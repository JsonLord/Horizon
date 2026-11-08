"""Trusted radar controller; local development / hosted read-only qualification."""
import argparse
import asyncio
import hashlib
import json
import os
import shutil
from datetime import UTC,datetime
from pathlib import Path
from src.research.reporting import atomic,dumps
from src.research.radar.contracts import RADARS,Digest,RadarManifest,cutoff,utc,stamp
from src.research.radar.pipeline import registry,run_collection,make_digest,State
from src.research.radar.storage import validate_tree,stage_digest,missing_weeks,read_json
from src.research.radar.publisher import GitHubData


def seal(root,radar,revision):
    validate_tree(root,radar)
    entries=[{'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(Path(root).rglob('*')) if p.is_file()]
    return {'schema_version':'1.0','radar_id':radar,'source_revision':revision,'files':entries}


def verify(root,proof,radar,revision):
    if proof!=seal(root,radar,revision):raise ValueError('Checkpoint manifest mismatch')
    return True


async def main(args):
    root=args.output/args.radar
    revision=os.getenv('GITHUB_SHA') or 'local-development'
    if args.command=='initialize':
        root.mkdir(parents=True,exist_ok=True)
        if any(root.iterdir()):raise ValueError('Initialization requires empty directory')
        atomic(root/'radar-manifest.json',dumps(RadarManifest(radar_id=args.radar).model_dump(mode='json')))
        atomic(root/'README.md',f'# {args.radar}\n\nUninitialized research data branch. No validated weekly digest yet.\nSee docs/RADAR_PULL_CONTRACT.md on the reviewed implementation branch.\n')
    elif args.command=='collect':
        if args.restore:
            GitHubData().read(args.radar,root)
        state,metrics=await run_collection(args.radar,root,source_revision=revision)
        for end in missing_weeks(root,args.radar,datetime.now(UTC)):
            digest=make_digest(state,end,root=root)
            # Partial digests remain outside the publishable tree.
            atomic(args.output/(args.radar+'-candidate-digest.json'),dumps(digest.model_dump(mode='json')))
            stage_digest(root,digest)
        atomic(args.output/(args.radar+'-collection-proof.json'),dumps({'radar_id':args.radar,'source_revision':revision,'metrics':metrics,'finding_count':len(state.findings),'failed_sources':len(state.failed_sources),'hosted':os.getenv('GITHUB_ACTIONS')=='true','run_id':os.getenv('GITHUB_RUN_ID')}))
    elif args.command=='digest':
        state=State.model_validate(read_json(root/'radar-state.json'))
        ends=[utc(args.week_end)] if args.week_end else missing_weeks(root,args.radar,datetime.now(UTC))
        for end in ends:
            digest=make_digest(state,end,root=root)
            atomic(args.output/(args.radar+'-candidate-digest.json'),dumps(digest.model_dump(mode='json')))
            stage_digest(root,digest,correction=args.correction)
    elif args.command=='validate':
        proof=read_json(args.output/(args.radar+'-checkpoint.json'))
        verify(root,proof,args.radar,revision)
    elif args.command=='publish':
        verify(root,read_json(args.output/(args.radar+'-checkpoint.json')),args.radar,revision)
        result=GitHubData().publish(args.radar,root)
        print(json.dumps(result)) # Actual commit obtained after commit creation.
    if args.command not in ('validate','publish'):
        atomic(args.output/(args.radar+'-checkpoint.json'),dumps(seal(root,args.radar,revision)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['initialize','collect','digest','validate','publish'])
    p.add_argument('--radar',choices=RADARS,required=True)
    p.add_argument('--output',type=Path,default=Path('data/radar'))
    p.add_argument('--restore',action='store_true')
    p.add_argument('--week-end',help='Recover an explicit Friday 18:00 UTC cutoff')
    p.add_argument('--correction',help='Explicit reviewed correction ID; original is retained')
    asyncio.run(main(p.parse_args()))
