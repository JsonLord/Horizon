"""Restore a verified durable archive before collection on an ephemeral runner."""

import shutil
import tempfile
from pathlib import Path

from .publisher import git, validate


def restore(root, remote, branch="intel"):
    if branch != "intel":
        raise ValueError("Only the reviewed intel branch is supported")
    root = Path(root)
    with tempfile.TemporaryDirectory(prefix="horizon-history-") as tmp:
        work = Path(tmp)
        git(work, "init", "-q")
        git(work, "remote", "add", "origin", remote)
        probe = git(work, "ls-remote", "--heads", "origin", branch)
        if not probe.stdout.strip():
            if (root / "intel/manifest.json").exists():
                raise ValueError("Missing remote history conflicts with local archive")
            return {"state": "bootstrap", "previous_snapshot_commit": None}
        git(work, "fetch", "--depth=1", "origin", branch)
        git(work, "checkout", "--detach", "FETCH_HEAD")
        if not (work / "intel/manifest.json").is_file():
            raise ValueError("Existing intel branch has no history manifest")
        validate(work)
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        # Never combine unverified local state with a purported remote baseline.
        if (root / "intel").exists():
            raise ValueError("Restore requires a fresh archive directory")
        from .reporting import Archive, atomic, dumps, markdown

        archive = Archive(work)
        atomic(root / "intel/manifest.json", dumps(archive.index()))
        for row in archive.list(limit=100):
            folder = Path(row["path"]).parent
            (root / folder).mkdir(parents=True, exist_ok=True)
            for name in ("report.json", "report.md", "manifest.json"):
                shutil.copy2(work / folder / name, root / folder / name)
        for pid in {r["profile_id"] for r in archive.list(limit=100)}:
            report = archive.latest(pid)
            if report:
                name = "world" if pid == "world/global" else pid
                atomic(root / f"intel/latest/{name}.json", dumps(report))
                atomic(root / f"intel/latest/{name}.md", markdown(report))
        return {"state": "restored", "previous_snapshot_commit": sha}
