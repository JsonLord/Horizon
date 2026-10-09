"""Validate all workflows, accounting narrowly for GitHub's newer queue: max."""

import argparse
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actionlint", default="actionlint")
    args = parser.parse_args()
    files = sorted(Path(".github/workflows").glob("*.yml"))
    for path in files:
        entries = re.findall(r"(?m)^\s+queue:\s*(.+)$", path.read_text())
        if entries and (
            path.name != "horizon-research.yml"
            or entries != ["max"]
            or "\n  cancel-in-progress: false\n  queue: max\n" not in path.read_text()
        ):
            raise ValueError(
                "Only static queue: max in the shared research concurrency group is supported"
            )
    # Upstream 1.7.12 understands native timezone but predates the documented
    # GitHub queue field. No other syntax/checks are ignored.
    code = subprocess.run(
        [
            args.actionlint,
            "-ignore",
            r'^unexpected key "queue" for "concurrency" section\.',
            *[str(p) for p in files],
        ]
    ).returncode
    if code:
        raise SystemExit(code)
    print(
        "All workflows validated; narrow actionlint exception: documented concurrency.queue=max"
    )


if __name__ == "__main__":
    main()
