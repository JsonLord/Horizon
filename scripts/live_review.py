"""Run approved real-source domains without any publisher or production writes."""
import argparse
import asyncio
from pathlib import Path
from src.research.live_review import DOMAINS, ReviewPack, evaluate, export_notices, portfolio
from src.research.reporting import atomic, dumps

async def main(args):
    domains = list(DOMAINS) if args.domain == 'all' else [args.domain]
    packs = []
    for domain in domains:
        packs.append(await evaluate(domain, args.output))
    if len(domains) == 7:
        atomic(args.output / 'INDEX.md', portfolio(packs))
    atomic(args.output / 'review.schema.json', dumps(ReviewPack.model_json_schema()))
    if args.export_notices: export_notices(args.output)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--domain', choices=['all', *DOMAINS], default='all')
    p.add_argument('--output', type=Path, default=Path('data/live-review'))
    p.add_argument('--export-notices', action='store_true')
    asyncio.run(main(p.parse_args()))
