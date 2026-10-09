"""Publish only validated bounded research artifacts, never source checkout files."""

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from .reporting import Archive, Manifest


def git(root, *args, check=True):
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )
    if check and result.returncode:
        raise RuntimeError(
            "Git operation failed: "
            + args[0]
            + " (authorization, branch rules or connectivity may block publication)"
        )
    return result


def validate(root):
    root = Path(root)
    archive = Archive(root)
    for row in archive.list(limit=100):
        report = archive.get(row["report_id"])
        if report["question"]:
            raise ValueError(
                "Private/ad hoc questions are export-only; publish approved scheduled profiles"
            )
        ids = {s["source_id"] for s in report["sources"]}
        if any(not set(f["source_ids"]) <= ids for f in report["findings"]):
            raise ValueError("Dangling evidence")
        manifest_path = (root / row["path"]).parent / "manifest.json"
        manifest = Manifest.model_validate_json(manifest_path.read_text())
        for a in manifest.artifacts:
            path = (root / a["path"]).resolve()
            if (
                not path.is_relative_to(root.resolve())
                or path.stat().st_size > 1_000_000
            ):
                raise ValueError("Unsafe artifact")
            data = path.read_bytes()
            if (
                len(data) != a["bytes"]
                or hashlib.sha256(data).hexdigest() != a["sha256"]
            ):
                raise ValueError("Checksum mismatch")
    return True


def publish(root, remote, branch="intel", dry_run=False):
    if branch != "intel":
        raise ValueError("Only intel archive branch supported")
    validate(root)
    # bounded optimistic retry merges archive manifests against a freshly fetched branch
    for attempt in range(3):
        with tempfile.TemporaryDirectory(prefix="horizon-publish-") as tmp:
            work = Path(tmp)
            git(work, "init", "-q")
            git(work, "remote", "add", "origin", remote)
            probe = git(work, "ls-remote", "--heads", "origin", branch)
            if probe.stdout.strip():
                git(work, "fetch", "--depth=1", "origin", branch)
                git(work, "checkout", "-B", branch, "FETCH_HEAD")
            else:
                git(work, "checkout", "--orphan", branch)
            existing = Archive(work).index()
            incoming = Archive(root).index()
            # Copy only schema/known report trees; never .env, jobs or prompts in logs.
            for row in incoming["reports"]:
                src = Path(root) / row["path"]
                dst = work / row["path"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                for filename in ("report.json", "report.md", "manifest.json"):
                    shutil.copy2(src.parent / filename, dst.parent / filename)
            merged = {r["report_id"]: r for r in existing["reports"]}
            merged.update({r["report_id"]: r for r in incoming["reports"]})
            rows = sorted(merged.values(), key=lambda r: r["created_at"], reverse=True)[
                :100
            ]
            from .reporting import atomic, dumps, markdown

            atomic(
                work / "intel/manifest.json",
                dumps({"schema_version": "1.0", "reports": rows}),
            )
            # Prune versioned reports not retained in the bounded index.
            retained = {str((work / r["path"]).parent) for r in rows}
            for report_path in (work / "intel/reports").rglob("report.json"):
                if str(report_path.parent) not in retained:
                    shutil.rmtree(report_path.parent)
            seen = set()
            for row in rows:
                if row["profile_id"] in seen or row["status"] not in (
                    "complete",
                    "partial",
                ):
                    continue
                seen.add(row["profile_id"])
                report = Archive(work).get(row["report_id"])
                latest = (
                    "world"
                    if row["profile_id"] == "world/global"
                    else row["profile_id"]
                )
                atomic(work / f"intel/latest/{latest}.json", dumps(report))
                atomic(work / f"intel/latest/{latest}.md", markdown(report))
            events = Path(root) / "intel/events"
            if events.exists():
                for p in events.rglob("*.jsonl"):
                    dst = work / p.relative_to(root)
                    old = (
                        [line for line in dst.read_text().splitlines() if line.strip()]
                        if dst.exists()
                        else []
                    )
                    atomic(
                        dst,
                        "\n".join(
                            list(dict.fromkeys(old + p.read_text().splitlines()))[
                                -1000:
                            ]
                        )
                        + "\n",
                    )
            for old_event in sorted((work / "intel/events").rglob("events.jsonl"))[
                :-30
            ]:
                old_event.unlink()
            schemas = Path(__file__).resolve().parents[2] / "schemas"
            if schemas.exists():
                shutil.copytree(schemas, work / "schemas", dirs_exist_ok=True)
            atomic(
                work / "README.md",
                "# Horizon research archive\n\nRead intel/manifest.json and intel/latest/world.json. Reports are bounded source-attributed extracts, not exhaustive or independently verified news.\n",
            )
            validate(work)
            git(work, "add", "intel", "schemas", "README.md")
            git(
                work,
                "-c",
                "user.name=Horizon Actions",
                "-c",
                "user.email=actions@users.noreply.github.com",
                "commit",
                "-m",
                "Publish Horizon research",
                "--allow-empty",
            )
            sha = git(work, "rev-parse", "HEAD").stdout.strip()
            if dry_run:
                return {"publication_status": "dry_run", "commit": sha}
            result = git(
                work, "push", "origin", "HEAD:refs/heads/" + branch, check=False
            )
            if not result.returncode:
                return {"publication_status": "published", "commit": sha, "ref": branch}
    raise RuntimeError(
        "Publication denied or concurrent updates exceeded bounded retries; no force push attempted"
    )
