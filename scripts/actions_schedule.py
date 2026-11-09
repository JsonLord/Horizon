"""Render reviewed schedule policy locally; never enable workflows through GitHub."""
import argparse
import json
import re
from pathlib import Path
from src.research.profiles import ROOT


def schedule_block(text,crons):
    # Only our three controllers use this exact top-level schedule shape. Work
    # with source text, preserving comments, expressions and every other event.
    text=re.sub(r'^  schedule:\n(?:    [^\n]*\n)*','',text,flags=re.M)
    block='  schedule:\n'+''.join("    - cron: '"+cron+"'\n" for cron in crons) if crons else ''
    if '\non:\n' not in text:raise ValueError('Missing workflow events')
    return text.replace('\non:\n','\non:\n'+block,1)


def plan(root=ROOT):
    root=Path(root);p=json.loads((root/'config/actions-schedules.json').read_text())
    radar=json.loads((root/'config/radar/registry.json').read_text())
    funding=json.loads((root/'config/funding-research.json').read_text())
    if p['schema_version']!='1.0' or p['radar']['enabled']!=radar['schedule_enabled'] or p['funding']['enabled']!=funding['schedule_enabled'] or p['radar']['second_daily_run_enabled']!=radar['second_daily_run_enabled']:raise ValueError('Schedule policy/registry mismatch')
    if not p['world']['enabled']:raise ValueError('Disabling existing world cadence requires separate review')
    crons={
        'horizon-intel.yml':[p['world']['cron']],
        'radar-fleet.yml':([p['radar']['daily_cron']]+([p['radar']['second_daily_cron']] if p['radar']['second_daily_run_enabled'] else [])+[p['radar']['digest_cron']]) if p['radar']['enabled'] else [],
        'funding-research.yml':[p['funding']['cron']] if p['funding']['enabled'] else []}
    if p['radar']['digest_cron']!='0 18 * * 5':raise ValueError('Friday digest cutoff must remain 18:00 UTC')
    for values in crons.values():
        if any(not re.fullmatch(r'[0-9*/, -]+',c) or len(c.split())!=5 for c in values):raise ValueError('Invalid cron')
    return {name:schedule_block((root/'.github/workflows'/name).read_text(),values) for name,values in crons.items()}


def apply(root=ROOT,check=True):
    for name,text in plan(root).items():
        path=Path(root)/'.github/workflows'/name
        if path.read_text()!=text:
            if check:raise ValueError('Workflow schedule differs from policy: '+name)
            path.write_text(text)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--check',action='store_true');group.add_argument('--render',action='store_true');args=p.parse_args();apply(check=not args.render)
