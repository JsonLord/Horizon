import asyncio
import json

import httpx
import pytest

from src.control.controller import Controller
from src.control.github import ControlError
from src.research.reporting import Archive
from src.research.service import ResearchService
from tests.control_api import API, CODE
from tests.test_research import fixture_item


def run(coro):
    return asyncio.run(coro)


def controller(api, tmp_path):
    return Controller(api.client(), state_dir=tmp_path / "journal")


def published(api, tmp_path, rid=1001, schedule_id=None):
    async def collect(p, q):
        return [fixture_item()], [{"source": "rss", "status": "ok", "items": 1}]

    async def execute():
        s = ResearchService(tmp_path / "archive", collector=collect)
        j = await s.submit({"profile_id": "institutions/ecb"})
        await s.wait(j["job_id"])
        r = s.archive.get(j["job_id"])
        r["workflow"].update(
            run_id=str(rid),
            source_commit=CODE,
            request_id="fixture-request",
            ref="main",
            effective_lookback_hours=48,
        )
        if schedule_id:
            r["schedule"] = {"schedule_id": schedule_id}
        s.archive.write(r)

    run(execute())
    api.add_archive(tmp_path / "archive")
    return Archive(tmp_path / "archive").index()["reports"][0]


def test_dispatch_real_run_response_and_idempotency(tmp_path):
    api = API()
    c = controller(api, tmp_path)

    async def check():
        first = await c.dispatch("institutions/ecb", 48, "fixture-request")
        assert first["run_id"] == 1001 and first["source_commit"] == CODE
        assert first["inputs"]["request_id"] == "fixture-request"
        again = await c.dispatch("institutions/ecb", 48, "fixture-request")
        assert again["reused"] and api.dispatch_count == 1
        with pytest.raises(ControlError, match="different"):
            await c.dispatch("institutions/ecb", 72, "fixture-request")
        fresh = controller(api, tmp_path / "fresh")
        assert (await fresh.dispatch("institutions/ecb", 48, "fixture-request"))[
            "run_id"
        ] == 1001
        assert api.dispatch_count == 1

    run(check())


def test_204_only_correlated_fallback(tmp_path):
    api = API()
    api.dispatch_mode = "204"
    c = controller(api, tmp_path)
    result = run(c.dispatch("institutions/ecb", 48, "fallback"))
    assert result["run_id"] == 1001


def test_204_without_run_never_invents_or_reposts(tmp_path, monkeypatch):
    api = API()
    api.dispatch_mode = "204-empty"
    c = controller(api, tmp_path)

    async def immediate(n):
        return None

    monkeypatch.setattr(asyncio, "sleep", immediate)
    result = run(c.dispatch("institutions/ecb", 48, "unseen"))
    assert (
        result["run_id"] is None and result["status"] == "acknowledged_waiting_for_run"
    )
    assert (
        run(c.dispatch("institutions/ecb", 48, "unseen"))["status"]
        == "dispatch_uncertain"
    )
    assert api.dispatch_count == 1


def test_uncertain_dispatch_never_automatically_retries(tmp_path):
    api = API()
    api.dispatch_mode = "timeout"
    c = controller(api, tmp_path)
    with pytest.raises(ControlError) as error:
        run(c.dispatch("institutions/ecb", 48, "lost"))
    assert error.value.code == "GITHUB_WRITE_UNCERTAIN"
    assert (
        run(c.dispatch("institutions/ecb", 48, "lost"))["status"]
        == "dispatch_uncertain"
    )
    assert api.dispatch_count == 1


def test_rejects_invalid_disabled_profiles_and_refs(tmp_path):
    api = API()
    c = controller(api, tmp_path)
    for profile, hours, ref in [
        ("world/unknown", 48, None),
        ("world/global", 169, None),
        ("world/global", 48, "evil-ref"),
    ]:
        with pytest.raises((ValueError, ControlError)):
            run(c.dispatch(profile, hours, ref=ref))
    api.profile_enabled = False
    c = controller(api, tmp_path / "disabled")
    with pytest.raises((ValueError, ControlError)):
        run(c.dispatch("institutions/ecb"))
    assert api.dispatch_count == 0


def test_unauthorized_write_has_actionable_error(tmp_path):
    api = API()
    api.denied = True
    c = controller(api, tmp_path)
    with pytest.raises(ControlError) as error:
        run(c.dispatch("institutions/ecb", request_id="no-access"))
    assert error.value.code == "GITHUB_FORBIDDEN"
    assert not list((tmp_path / "journal").glob("*.json"))


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out"])
def test_workflow_failure_states(tmp_path, conclusion):
    api = API()
    api.create_run(status="completed", conclusion=conclusion)
    api.jobs[1001] = [
        {
            "id": 1,
            "name": "research / collect",
            "status": "completed",
            "conclusion": conclusion,
            "started_at": "2026-10-10T08:00:00Z",
            "completed_at": "2026-10-10T08:05:00Z",
            "steps": [{"name": "Collect", "conclusion": conclusion}],
        }
    ]
    result = run(controller(api, tmp_path).workflow_run(1001))
    assert result["runner_completed"] and not result["collection_succeeded"]
    assert result["publication_status"] == "not_observed" and result["failure_reason"]


def test_collection_success_publisher_failure_is_not_publication(tmp_path):
    api = API()
    api.create_run(status="completed", conclusion="failure")
    api.jobs[1001] = [
        {
            "id": 1,
            "name": "research / collect",
            "status": "completed",
            "conclusion": "success",
        },
        {
            "id": 2,
            "name": "research / publish",
            "status": "completed",
            "conclusion": "failure",
        },
    ]
    result = run(controller(api, tmp_path).workflow_run(1001))
    assert result["collection_succeeded"] and not result["publication_job_succeeded"]
    assert result["publication_status"] == "not_observed"


def test_exact_run_report_checksums_and_format(tmp_path):
    api = API()
    api.create_run(status="completed", conclusion="success")
    published(api, tmp_path)
    c = controller(api, tmp_path)

    async def check():
        for fmt in ["json", "markdown", "summary"]:
            result = await c.workflow_report(1001, "institutions/ecb", fmt)
            assert (
                result["publication_status"] == "verified"
                and result["publication_commit"]
            )
            assert "/" + result["archive_commit"] + "/" in result["links"]["json"]
        with pytest.raises(ControlError) as error:
            await c.workflow_report(1002, "institutions/ecb")
        assert error.value.code == "REPORT_NOT_PUBLISHED"
        with pytest.raises(ControlError):
            await c.workflow_report(1001, "world/global")

    run(check())


def test_successful_runner_without_requested_report(tmp_path):
    api = API()
    api.create_run(status="completed", conclusion="success")
    api.create_run(1002, status="completed", conclusion="success")
    published(api, tmp_path, rid=1002)
    api.jobs[1001] = [
        {
            "id": 1,
            "name": "research / collect",
            "status": "completed",
            "conclusion": "success",
        },
        {
            "id": 2,
            "name": "research / publish",
            "status": "completed",
            "conclusion": "success",
        },
    ]
    r = run(controller(api, tmp_path).workflow_run(1001))
    assert r["publication_job_succeeded"] and r["publication_status"] == "not_observed"


def test_tampered_report_rejected(tmp_path):
    api = API()
    api.create_run()
    row = published(api, tmp_path)
    api.archive_files[row["path"]] = api.archive_files[row["path"]].replace(
        b"European Central Bank announces decision",
        b"European Central Bank announces fiction",
    )
    with pytest.raises(ControlError) as error:
        run(controller(api, tmp_path).workflow_report(1001))
    assert error.value.code == "ARCHIVE_CHECKSUM_MISMATCH"


def test_schedule_lifecycle_prs_and_activation(tmp_path):
    api = API()
    c = controller(api, tmp_path)

    async def check():
        created = await c.change_schedule(
            "create",
            name="ECB weekdays",
            profile_id="institutions/ecb",
            cron="30 8 * * 1-5",
            timezone="Europe/Berlin",
            lookback_hours=24,
        )
        sid = created["schedule_id"]
        assert created["activation_state"] == "pending_review"
        listed = await c.list_schedules()
        assert any(p["schedule_id"] == sid for p in listed["pending_changes"])
        assert not any(s["schedule_id"] == sid for s in listed["schedules"])
        reused = await c.change_schedule(
            "create",
            name="ECB weekdays",
            profile_id="institutions/ecb",
            cron="30 8 * * 1-5",
            timezone="Europe/Berlin",
            lookback_hours=24,
        )
        assert reused["reused"] and len(api.prs) == 1
        api.merge(created)
        assert (await c.get_schedule(sid))["schedule"]["activation_state"] == "active"
        updated = await c.change_schedule("update", sid, lookback_hours=72)
        api.merge(updated)
        assert (await c.get_schedule(sid))["schedule"]["lookback_hours"] == 72
        paused = await c.change_schedule("pause", sid)
        assert paused["activation_state"] == "pending_review"
        api.merge(paused)
        assert (await c.get_schedule(sid))["schedule"]["activation_state"] == "paused"
        resumed = await c.change_schedule("resume", sid)
        api.merge(resumed)
        assert (await c.get_schedule(sid))["schedule"]["activation_state"] == "active"
        deleted = await c.change_schedule("delete", sid)
        api.merge(deleted)
        assert not any(
            s["schedule_id"] == sid for s in (await c.list_schedules())["schedules"]
        )

    run(check())
    assert not any(method == "PATCH" for method, _, _ in api.requests)
    assert not any(
        p.startswith("intel/")
        for method, path, payload in api.requests
        if path == "git/trees"
        for p in [r["path"] for r in payload["tree"]]
    )


def test_proposal_conflict_never_overwrites_branch(tmp_path):
    api = API()
    c = controller(api, tmp_path)

    async def check():
        fields = dict(
            name="CERN weekly",
            profile_id="institutions/cern",
            cron="15 7 * * 1",
            timezone="UTC",
            lookback_hours=168,
        )
        proposal = await c.change_schedule("create", **fields)
        api.prs = []
        api.commits[api.refs[proposal["branch"]]]["message"] = "Unrelated user work"
        with pytest.raises(ControlError) as error:
            await c.change_schedule("create", **fields)
        assert error.value.code == "PROPOSAL_CONFLICT"

    run(check())


def test_profile_proposal_and_permission_failure(tmp_path):
    api = API()
    c = controller(api, tmp_path)
    from src.research.profiles import load_profiles

    profile = load_profiles(include_registry=False)[
        "world/science-technology"
    ].model_dump(mode="json", by_alias=True)
    profile["profile_id"] = "examples/reviewed-target"
    result = run(c.propose_profile(profile))
    assert result["activation_state"] == "pending_review"
    api.fail_pr = True
    with pytest.raises(ControlError):
        run(c.change_schedule("pause", "daily-ecb"))


def test_schedule_history_includes_partial_reports(tmp_path):
    api = API()
    api.create_run(schedule_id="daily-ecb", status="completed", conclusion="success")
    row = published(api, tmp_path, schedule_id="daily-ecb")
    result = run(controller(api, tmp_path).schedule_runs("daily-ecb"))
    assert result["reports"][0]["report_id"] == row["report_id"]
    assert result["runs"][0]["run_id"] == 1001
    assert result["missed_execution_status"] == "unknown"


def test_unauthenticated_public_archive_read(tmp_path):
    api = API()
    api.create_run()
    published(api, tmp_path)
    github = api.client()
    github.token = None
    github._auth_checked = True
    result = run(
        Controller(github, state_dir=tmp_path / "public").workflow_report(1001)
    )
    assert result["publication_status"] == "verified"
    with pytest.raises(ControlError) as error:
        run(github.authenticate(required=True))
    assert error.value.code == "GITHUB_AUTH_REQUIRED"


def test_safe_get_retries_but_uncertain_write_stays_reserved(tmp_path, monkeypatch):
    api = API()
    calls = []

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    def flaky(req, path, payload):
        if path == "actions/runs":
            calls.append(path)
            if len(calls) < 3:
                return httpx.Response(503)
        if path.endswith("/dispatches"):
            return httpx.Response(503)

    api.extra = flaky
    c = controller(api, tmp_path)
    assert run(c.github.get("actions/runs"))["workflow_runs"] == []
    assert len(calls) == 3
    with pytest.raises(ControlError) as e:
        run(c.dispatch("institutions/ecb", request_id="server-lost"))
    assert e.value.code == "GITHUB_WRITE_UNCERTAIN"
    assert (
        run(c.dispatch("institutions/ecb", request_id="server-lost"))["status"]
        == "dispatch_uncertain"
    )
    assert sum(path.endswith("/dispatches") for _, path, _ in api.requests) == 1


def test_concurrent_local_dispatch_uses_one_request(tmp_path):
    api = API()
    c = controller(api, tmp_path)

    async def check():
        a, b = await asyncio.gather(
            c.dispatch("institutions/ecb", request_id="same-key"),
            c.dispatch("institutions/ecb", request_id="same-key"),
        )
        assert a["run_id"] == b["run_id"] and api.dispatch_count == 1

    run(check())


def test_pending_default_schedule_migration_is_not_active(tmp_path):
    api = API()
    api.prs = [
        {
            "html_url": "https://github.com/JsonLord/Horizon/pull/3",
            "body": "<!-- horizon-integration -->",
            "head": {"sha": CODE, "ref": "integration"},
        }
    ]
    api.trees["d" * 40] = {
        p: data
        for p, data in api.files.items()
        if not p.startswith("schedules/")
        and not p.startswith(".github/workflows/horizon-sched-")
    }
    api.commits["e" * 40] = {"sha": "e" * 40, "commit": {"tree": {"sha": "d" * 40}}}
    api.refs["main"] = "e" * 40
    result = run(controller(api, tmp_path).list_schedules())
    assert result["schedules"] == [] and len(result["pending_changes"]) == 5
    assert all(
        p["activation_state"] == "pending_review" for p in result["pending_changes"]
    )


def test_propose_source_uses_reviewed_assignments(tmp_path, monkeypatch):
    from src.research import registry

    api = API()
    c = controller(api, tmp_path)

    async def verified(url, feed_url=None, client=None):
        return "https://example.org/feed", {
            "entries": 1,
            "feed_title": "Fixture",
            "latest_published_at": None,
        }

    monkeypatch.setattr(registry, "discover", verified)
    result = run(
        c.propose_source("https://example.org/", "Reviewed example", ["world/global"])
    )
    assert result["activation_state"] == "pending_review" and result["kind"] == "source"
    branch = api.refs[result["branch"]]
    tree = api.trees[api.commits[branch]["commit"]["tree"]["sha"]]
    source = json.loads(tree["sources/registry.json"])["sources"][-1]
    assert source["profile_ids"] == ["world/global"]
    assert source["feed_url"] == "https://example.org/feed"


def test_changed_default_branch_blocks_proposal(tmp_path):
    api = API()
    c = controller(api, tmp_path)
    calls = 0

    def raced(req, path, payload):
        nonlocal calls
        if path == "commits/main":
            calls += 1
            if calls >= 2:
                moved = dict(api.commits[CODE])
                moved["sha"] = "f" * 40
                return httpx.Response(200, json=moved)

    api.extra = raced
    with pytest.raises(ControlError) as e:
        run(c.change_schedule("pause", "daily-ecb"))
    assert e.value.code == "PROPOSAL_CONFLICT"
    assert not any(path == "git/refs" for _, path, _ in api.requests)


def test_schedule_update_rejects_commands_and_disabled_profile(tmp_path):
    api = API()
    c = controller(api, tmp_path)
    with pytest.raises(ValueError):
        run(c.change_schedule("update", "daily-ecb", command="curl somewhere"))
    with pytest.raises(ValueError):
        run(c.change_schedule("update", "daily-ecb", profile_id="world/not-reviewed"))
    assert not any(method != "GET" for method, _, _ in api.requests)


def test_source_sha_mismatch_rejected_even_for_markdown(tmp_path):
    api = API()
    api.create_run()
    published(api, tmp_path)
    api.runs[1001]["head_sha"] = "f" * 40
    with pytest.raises(ControlError) as error:
        run(controller(api, tmp_path).workflow_report(1001, format="markdown"))
    assert error.value.code == "ARCHIVE_IDENTITY_MISMATCH"


def test_returned_run_id_survives_metadata_propagation_delay(tmp_path):
    api = API()

    def delayed(req, path, payload):
        if path == "actions/runs/1001":
            return httpx.Response(404)

    api.extra = delayed
    result = run(
        controller(api, tmp_path).dispatch(
            "institutions/ecb", request_id="details-propagating"
        )
    )
    assert result["run_id"] == 1001 and result["status"] == "submitted"
    assert result["source_commit"] is None
    assert api.dispatch_count == 1
