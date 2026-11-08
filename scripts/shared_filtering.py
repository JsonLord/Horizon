"""Local staging qualification, feedback and live OpenAI-compatible smoke test."""
import argparse
import asyncio
import json
import hashlib
import shutil
import sqlite3
from pathlib import Path
from src.research.filtering import FilterPolicy,HorizonFilterPipeline
from src.research.filtering.engine import DurableCheckpointStore,FeedbackStore
from src.research.filtering.provider import DecisionModelProvider,COMMANDS
from src.research.reporting import atomic,dumps

async def qualify(output,restore=False):
    output.mkdir(parents=True,exist_ok=True)
    if restore:
        manifest=json.loads((output/'manifest.json').read_text())
        if hashlib.sha256((output/'checkpoint.sqlite').read_bytes()).hexdigest()!=manifest['sha256']:raise ValueError('Checkpoint checksum mismatch')
        with sqlite3.connect('file:'+str((output/'checkpoint.sqlite').resolve())+'?mode=ro',uri=True) as db:
            if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Invalid SQLite snapshot')
        # Deliberate interrupted working state, recovered solely from validated backup.
        (output/'state.sqlite').write_bytes(b'interrupted working write')
        shutil.copyfile(output/'checkpoint.sqlite',output/'state.sqlite')
    state=DurableCheckpointStore(output/'state.sqlite')
    provider=DecisionModelProvider()
    # A disclosed inference fixture, never a published research finding.
    payload={'summary':'Public fixture: accessibility testing tool adds keyboard-navigation checks.','evidence':[{'id':'smoke-public','snippet':'The fixture release adds keyboard-navigation checks.'}]}
    decision,meta=await provider.decide('relevance',payload)
    proof={'live_inference':bool(decision),'provider':meta,'decision':decision.model_dump() if decision else None,'policies':[]}
    for profile in ('examples/ai-usability','funding/de-eu','world/global'):
        policy=FilterPolicy.load(profile)
        fixture={'finding_id':'fixture-'+profile.replace('/','-'),'event_id':'fixture-event','summary':payload['summary'],'source_ids':['smoke-public'],'evidence':[{'source_id':'smoke-public','snippet':payload['evidence'][0]['snippet']}]}
        result=await HorizonFilterPipeline(policy,state,provider).run([fixture],[{'source_id':'smoke-public'}],hard_statuses={'fixture-event':'ELIGIBILITY_UNKNOWN'} if profile.startswith('funding/') else None)
        proof['policies'].append({'profile':profile,'fixture_decisions':result})
    state.snapshot(str(output/'checkpoint.sqlite'));state.close()
    restored=DurableCheckpointStore(output/'checkpoint.sqlite')
    proof['restoration_verified']=restored.get('history','world/global|fixture-world-global') is not None
    restored.close()
    proof['command_qualification']=[]
    command_state=DurableCheckpointStore(output/'commands.sqlite')
    for profile in ('examples/ai-usability','funding/de-eu','world/global'):
        for command in COMMANDS:
            key=provider.identity()+'|'+profile+'|'+command
            entry=command_state.get('live-command',key)
            if entry is None:
                response,metadata=await provider.decide(command,{**payload,'topics':FilterPolicy.load(profile).topics,'previous':[]})
                entry={'profile':profile,'command':command,'decision':response.model_dump() if response else None,'provider':metadata}
                if response:command_state.put('live-command',key,entry)
            proof['command_qualification'].append(entry)
    command_state.close()
    proof['all_commands_live_validated']=all(e['decision'] is not None for e in proof['command_qualification'])
    proof['configuration']={'base_url_present':bool(provider.base),'model_present':bool(provider.model),'key_present':bool(provider.key),'mode_is_openai_chat':provider.mode=='openai_chat'}
    proof['provider_requests']=provider.requests
    proof['cache_hits']=sum(r.get('cache_hit',False) for p in proof['policies'] for r in p['fixture_decisions'])
    proof['restored_prior_runner_checkpoint']=restore
    atomic(output/'manifest.json',dumps({'schema_version':'1.0','sha256':hashlib.sha256((output/'checkpoint.sqlite').read_bytes()).hexdigest()}))
    atomic(output/'proof.json',dumps(proof))
    # Safe public proof: omit endpoint, credentials and retrieved content.
    public={k:proof[k] for k in ('live_inference','provider','restoration_verified','restored_prior_runner_checkpoint','provider_requests','cache_hits')}
    public['profiles']=[p['profile'] for p in proof['policies']]
    print('::notice title=shared-filtering-smoke::'+json.dumps(public).replace('%','%25').replace('\n','%0A'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--restore',action='store_true');p.add_argument('--feedback',choices=['more_like_this','less_like_this','important_but_not_actionable']);p.add_argument('--profile');p.add_argument('--topics',nargs='*',default=[]);p.add_argument('--sources',nargs='*',default=[]);p.add_argument('--item');p.add_argument('--reason',default='Operator review');p.add_argument('--output',type=Path,default=Path('data/shared-filtering'));args=p.parse_args()
    if args.feedback:
        if not args.profile or not args.item:p.error('Feedback needs --profile and --item')
        state=DurableCheckpointStore(args.output/'state.sqlite');FeedbackStore(state).add(args.profile,args.item,args.feedback,args.reason,topics=args.topics,sources=args.sources);state.close()
    else:asyncio.run(qualify(args.output,args.restore))
