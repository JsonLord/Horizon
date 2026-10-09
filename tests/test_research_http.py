import importlib

from fastapi.testclient import TestClient

from src.research.service import ResearchService


def test_read_and_disabled_writes(tmp_path, monkeypatch):
    api = importlib.import_module("src.api.app")
    monkeypatch.setattr(api, "service", ResearchService(tmp_path))
    monkeypatch.delenv("HORIZON_AGENT_TOKEN", raising=False)

    async def unavailable(*a, **kw):
        return None

    monkeypatch.setattr(api.remote, "list", unavailable)
    with TestClient(api.app) as client:
        for path in [
            "/health",
            "/ready",
            "/v1/info",
            "/v1/profiles",
            "/v1/profiles/world/global",
            "/v1/reports",
            "/v1/changes",
            "/api-docs",
            "/openapi.json",
            "/",
        ]:
            assert client.get(path).status_code == 200, path
        assert (
            client.post("/v1/jobs", json={"profile_id": "world/global"}).status_code
            == 403
        )
        assert client.get("/v1/jobs/unknown").status_code == 403
        assert client.get("/v1/reports?limit=101").status_code == 422
        assert client.get("/v1/profiles/unknown").json()["ok"] is False


def test_authorized_job_and_privacy(tmp_path, monkeypatch):
    api = importlib.import_module("src.api.app")

    async def fixture(p, q):
        return [], [{"source": "google_news", "status": "ok", "items": 0}]

    monkeypatch.setattr(api, "service", ResearchService(tmp_path, collector=fixture))
    monkeypatch.setenv("HORIZON_AGENT_TOKEN", "fixture-token")
    api.calls.clear()

    async def unavailable(*a, **kw):
        return None

    monkeypatch.setattr(api.remote, "list", unavailable)

    async def missing(*a):
        raise KeyError("missing")

    monkeypatch.setattr(api.remote, "get", missing)
    with TestClient(api.app) as client:
        headers = {"Authorization": "Bearer fixture-token"}
        assert (
            client.post(
                "/v1/jobs",
                json={"profile_id": "world/global"},
                headers={"Authorization": "Bearer wrong"},
            ).status_code
            == 401
        )
        result = client.post(
            "/v1/jobs",
            json={
                "profile_id": "world/global",
                "question": "private fixture question",
                "idempotency_key": "test",
            },
            headers=headers,
        )
        assert result.status_code == 202
        jid = result.json()["job_id"]
        import time

        for _ in range(50):
            job = client.get("/v1/jobs/" + jid, headers=headers).json()
            if job["status"] not in ("queued", "running"):
                break
            time.sleep(0.01)
        assert job["status"] == "completed"
        assert client.get("/v1/reports/" + jid).status_code in (401, 403, 404)
        assert client.get("/v1/reports").json()["reports"] == []
        assert client.get("/v1/reports/" + jid, headers=headers).status_code == 200


def test_request_size_ceiling(monkeypatch, tmp_path):
    api = importlib.import_module("src.api.app")
    monkeypatch.setattr(api, "service", ResearchService(tmp_path))
    with TestClient(api.app) as client:
        result = client.post(
            "/v1/jobs",
            content=b"x" * 17000,
            headers={"Content-Type": "application/json"},
        )
        assert (
            result.status_code == 413
            and result.json()["error"]["code"] == "BODY_TOO_LARGE"
        )
