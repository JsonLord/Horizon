"""In-memory GitHub REST fixture exercising the real HTTP/controller clients."""

import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import httpx

from src.control.github import GitHub

CODE = "a" * 40
TREE = "b" * 40
INTEL = "c" * 40


class API:
    def __init__(self):
        self.files = {
            str(p): p.read_bytes()
            for root in ["profiles", "sources", "schedules", ".github/workflows"]
            for p in Path(root).rglob("*")
            if p.is_file()
        }
        self.trees = {TREE: dict(self.files)}
        self.commits = {
            CODE: {
                "sha": CODE,
                "commit": {"tree": {"sha": TREE}},
                "message": "base",
                "parents": [],
            }
        }
        self.refs = {"main": CODE, "authorized-test": CODE}
        self.runs = {}
        self.jobs = {}
        self.prs = []
        self.blobs = {}
        self.requests = []
        self.dispatch_mode = "details"
        self.dispatch_count = 0
        self.denied = False
        self.fail_pr = False
        self.profile_enabled = True
        self.bad_response = False
        self.archive_files = None
        self.extra = None

    def client(self):
        return GitHub(
            client=httpx.AsyncClient(transport=httpx.MockTransport(self.handle)),
            token="fixture-token",
        )

    def add_archive(self, root):
        self.archive_files = {
            str(p.relative_to(root)): p.read_bytes()
            for p in Path(root).rglob("*")
            if p.is_file()
        }
        self.trees[INTEL] = self.archive_files
        self.commits[INTEL] = {
            "sha": INTEL,
            "commit": {"tree": {"sha": INTEL}},
            "message": "Publish",
            "parents": [],
        }
        self.refs["intel"] = INTEL

    def create_run(
        self,
        rid=1001,
        profile="institutions/ecb",
        request="fixture-request",
        ref="main",
        status="queued",
        conclusion=None,
        schedule_id=None,
    ):
        name = (
            f"Horizon {profile} [request={request}] [hours=48]"
            if not schedule_id
            else f"Horizon schedule {schedule_id} [{profile}]"
        )
        path = (
            ".github/workflows/horizon-intel.yml"
            if not schedule_id
            else f".github/workflows/horizon-sched-{schedule_id}.yml"
        )
        run = {
            "id": rid,
            "html_url": f"https://github.com/JsonLord/Horizon/actions/runs/{rid}",
            "head_sha": self.refs[ref],
            "head_branch": ref,
            "status": status,
            "conclusion": conclusion,
            "created_at": "2026-10-10T08:00:00Z",
            "run_started_at": "2026-10-10T08:00:01Z",
            "display_title": name,
            "path": path,
        }
        self.runs[rid] = run
        self.jobs[rid] = []
        return run

    def response(self, status=200, data=None):
        return httpx.Response(status, json=data if data is not None else {})

    def handle(self, request):
        path = unquote(request.url.path).split("/repos/JsonLord/Horizon/", 1)[-1]
        payload = json.loads(request.content) if request.content else None
        self.requests.append((request.method, path, payload))
        if self.extra:
            override = self.extra(request, path, payload)
            if override is not None:
                return override
        if self.denied and request.method != "GET":
            return self.response(403)
        if path.startswith("commits/"):
            ref = path[len("commits/") :]
            sha = self.refs.get(ref, ref)
            return (
                self.response(data=self.commits[sha])
                if sha in self.commits
                else self.response(404)
            )
        if path == "commits":
            return self.response(data=[{"sha": INTEL}])
        if path.startswith("contents/"):
            ref = request.url.params.get("ref", "main")
            sha = self.refs.get(ref, ref)
            commit = self.commits.get(sha)
            files = (
                self.trees.get(commit["commit"]["tree"]["sha"], {}) if commit else {}
            )
            target = path[len("contents/") :]
            if target not in files:
                return self.response(404)
            data = files[target]
            if not self.profile_enabled and target == "profiles/institutions/ecb.json":
                obj = json.loads(data)
                obj["enabled"] = False
                data = json.dumps(obj).encode()
            return self.response(
                data={
                    "type": "file",
                    "size": len(data),
                    "encoding": "base64",
                    "content": base64.b64encode(data).decode(),
                }
            )
        if path.startswith("git/trees/"):
            sha = path.split("/")[-1]
            return self.response(
                data={
                    "tree": [
                        {"path": p, "type": "blob", "sha": "f" * 40}
                        for p in self.trees[sha]
                    ],
                    "truncated": False,
                }
            )
        if path == "git/blobs":
            data = payload["content"].encode()
            sha = hashlib.sha1(data).hexdigest()
            self.blobs[sha] = data
            return self.response(201, {"sha": sha})
        if path == "git/trees":
            files = dict(self.trees[payload["base_tree"]])
            for row in payload["tree"]:
                if row["sha"] is None:
                    files.pop(row["path"], None)
                else:
                    files[row["path"]] = self.blobs[row["sha"]]
            sha = hashlib.sha1(repr(sorted(files.items())).encode()).hexdigest()
            self.trees[sha] = files
            return self.response(201, {"sha": sha})
        if path == "git/commits":
            sha = hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            self.commits[sha] = {
                "sha": sha,
                "commit": {"tree": {"sha": payload["tree"]}},
                "message": payload["message"],
                "parents": [{"sha": s} for s in payload["parents"]],
            }
            return self.response(201, {"sha": sha})
        if path.startswith("git/commits/"):
            c = self.commits[path.split("/")[-1]]
            return self.response(data={**c, "tree": c["commit"]["tree"]})
        if path.startswith("git/ref/heads/"):
            name = path[len("git/ref/heads/") :]
            return (
                self.response(data={"object": {"sha": self.refs[name]}})
                if name in self.refs
                else self.response(404)
            )
        if path == "git/refs":
            name = payload["ref"][len("refs/heads/") :]
            if name in self.refs:
                return self.response(422)
            self.refs[name] = payload["sha"]
            return self.response(201, {"ref": payload["ref"]})
        if path == "pulls":
            if request.method == "POST":
                if self.fail_pr:
                    return self.response(403)
                pr = {
                    **payload,
                    "number": len(self.prs) + 1,
                    "html_url": "https://github.com/JsonLord/Horizon/pull/"
                    + str(len(self.prs) + 1),
                    "head": {"ref": payload["head"], "sha": self.refs[payload["head"]]},
                }
                self.prs.append(pr)
                return self.response(201, pr)
            head = request.url.params.get("head")
            return self.response(
                data=[
                    p
                    for p in self.prs
                    if not head or head.split(":", 1)[-1] == p["head"]["ref"]
                ]
            )
        if path.endswith("/dispatches"):
            self.dispatch_count += 1
            if self.dispatch_mode == "timeout":
                raise httpx.ReadTimeout("fixture response lost")
            rid = 1000 + self.dispatch_count
            run = self.create_run(
                rid,
                payload["inputs"]["profile_id"],
                payload["inputs"]["request_id"],
                payload["ref"],
            )
            run["display_title"] = run["display_title"].replace(
                "[hours=48]", f"[hours={payload['inputs']['lookback_hours']}]"
            )
            if self.dispatch_mode == "204-empty":
                self.runs.pop(rid)
            return (
                httpx.Response(204)
                if self.dispatch_mode.startswith("204")
                else self.response(
                    data={"workflow_run_id": rid, "html_url": run["html_url"]}
                )
            )
        if path == "actions/runs":
            return self.response(data={"workflow_runs": list(self.runs.values())[::-1]})
        if path.startswith("actions/runs/"):
            rid = int(path.split("/")[2])
            if rid not in self.runs:
                return self.response(404)
            if path.endswith("/jobs"):
                return self.response(data={"jobs": self.jobs[rid]})
            return self.response(data=self.runs[rid])
        if path.startswith("actions/workflows/"):
            name = path.split("/")[2]
            if path.endswith("/runs"):
                return self.response(
                    data={
                        "workflow_runs": [
                            r
                            for r in self.runs.values()
                            if r["path"].split("/")[-1] == name
                        ][::-1]
                    }
                )
            sha = self.refs["main"]
            files = self.trees[self.commits[sha]["commit"]["tree"]["sha"]]
            return (
                self.response(data={"id": 123, "state": "active"})
                if ".github/workflows/" + name in files
                else self.response(404)
            )
        raise AssertionError((request.method, path, payload))

    def merge(self, result):
        self.refs["main"] = self.refs[result["branch"]]
        self.prs = [p for p in self.prs if p["head"]["ref"] != result["branch"]]
