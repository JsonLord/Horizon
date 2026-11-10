"""Run a read-only held-out two-stage filtering experiment."""
import argparse
import asyncio
import os
from pathlib import Path

from src.research.two_stage_experiment import run_experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=Path('data/two-stage-experiment'))
    parser.add_argument('--run-id', default=os.getenv('GITHUB_RUN_ID'))
    args = parser.parse_args()
    if not args.run_id:
        parser.error('--run-id or GITHUB_RUN_ID is required')
    output = args.output_root / args.run_id
    report = asyncio.run(run_experiment(output, run_id=args.run_id))
    print(f"experiment={args.run_id} complete_domains={sum(d['complete'] for d in report['domains'].values())}/5 output={output}")


if __name__ == '__main__':
    main()
