"""Single-port read-only dashboard with optional authenticated ephemeral jobs."""

import os
import secrets
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi import Request as HTTPRequest
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from src.research.remote import RemoteArchive
from src.research.reporting import markdown
from src.research.service import Request, ResearchService

service = ResearchService()
remote = RemoteArchive()
calls = []


@asynccontextmanager
async def lifespan(app):
    yield
    for task in service.tasks.values():
        if not task.done():
            task.cancel()


app = FastAPI(title="Horizon research", docs_url="/api-docs", lifespan=lifespan)


def error(code, message, status):
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": {"code": code, "message": message}},
    )


@app.middleware("http")
async def bounded_body(request: HTTPRequest, call_next):
    if request.method in ("POST", "PUT", "PATCH"):
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > 16384:
                    return error("BODY_TOO_LARGE", "Request body exceeds 16 KB", 413)
            except ValueError:
                return error("INVALID_REQUEST", "Invalid content length", 400)
        data = b""
        async for chunk in request.stream():
            data += chunk
            if len(data) > 16384:
                return error("BODY_TOO_LARGE", "Request body exceeds 16 KB", 413)
        request._body = data
    return await call_next(request)


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return error(
        "INTERNAL_ERROR",
        "Operation failed; no private diagnostic payload is exposed",
        500,
    )


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error("HTTP_" + str(exc.status_code), str(exc.detail), exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return error("INVALID_REQUEST", "Request does not satisfy the bounded schema", 422)


@app.exception_handler(KeyError)
async def not_found(request, exc):
    return error("NOT_FOUND", "Resource not found", 404)


@app.exception_handler(ValueError)
async def bad_request(request, exc):
    return error("INVALID_REQUEST", "Invalid request", 422)


@app.exception_handler(OverflowError)
async def full(request, exc):
    return error("QUEUE_FULL", "Queue is full; retry later", 429)


async def authorized(request: HTTPRequest):
    token = os.getenv("HORIZON_AGENT_TOKEN")
    if not token:
        raise HTTPException(403, "Remote writes are disabled")
    supplied = request.headers.get("authorization", "")
    if not secrets.compare_digest(supplied, "Bearer " + token):
        raise HTTPException(401, "Authorization required")
    return "authorized_agent"


async def write_authorized(request: HTTPRequest, identity=Depends(authorized)):
    now = time.monotonic()
    calls[:] = [x for x in calls if now - x < 60]
    if len(calls) >= 10:
        raise HTTPException(429, "Rate limit exceeded")
    calls.append(now)
    return identity


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ready")
def ready():
    return {
        "ok": True,
        "analysis_mode": os.getenv("HORIZON_AI_MODE", "auto"),
        "deterministic_fallback": True,
        "model_configured": bool(
            os.getenv("HORIZON_LLM_BASE_URL") and os.getenv("HORIZON_LLM_MODEL")
        ),
        "archive_connectivity": remote.status,
        "profiles": len(service.profiles),
    }


@app.get("/v1/info")
def info():
    return {
        "version": "0.1.0",
        "modes": ["world_radar", "institution_watch", "research_job"],
        "sources": ["gdelt", "google_news", "rss"],
        "analysis_mode": os.getenv("HORIZON_AI_MODE", "auto"),
        "publication_mode": "local_only",
        "remote_writes": bool(os.getenv("HORIZON_AGENT_TOKEN")),
        "archive_ref": os.getenv("HORIZON_ARCHIVE_REF", "intel"),
        "capabilities": {
            "public_read": True,
            "ephemeral_jobs": bool(os.getenv("HORIZON_AGENT_TOKEN")),
            "durable_publication": "GitHub Actions",
        },
    }


@app.get("/v1/profiles")
def profiles():
    return {
        "profiles": [p.model_dump(by_alias=True) for p in service.profiles.values()]
    }


@app.get("/v1/profiles/{profile_id:path}")
def profile(profile_id: str):
    return service.profile(profile_id).model_dump(by_alias=True)


@app.get("/v1/reports")
async def reports(
    request: HTTPRequest,
    profile_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    rows = await remote.list(profile_id, limit, offset)
    local = []
    if (
        rows is None
        and os.getenv("HORIZON_AGENT_TOKEN")
        and secrets.compare_digest(
            request.headers.get("authorization", ""),
            "Bearer " + os.environ["HORIZON_AGENT_TOKEN"],
        )
    ):
        local = service.archive.list(profile_id, limit, offset)
    return {
        "reports": rows if rows is not None else local,
        "origin": "published" if rows is not None else "local_ephemeral",
    }


@app.get("/v1/reports/{report_id}")
async def report(request: HTTPRequest, report_id: str, format: str = "json"):
    try:
        result = await remote.get(report_id)
    except (KeyError, ValueError):
        await authorized(request)
        result = service.archive.get(report_id)
    return (
        PlainTextResponse(markdown(result), media_type="text/markdown")
        if format == "markdown"
        else result
    )


@app.get("/v1/changes")
async def changes(
    request: HTTPRequest, profile_id: str | None = None, since: str | None = None
):
    rows = await remote.list(profile_id, limit=100)
    if rows is None:
        token = os.getenv("HORIZON_AGENT_TOKEN")
        allowed = bool(
            token
            and secrets.compare_digest(
                request.headers.get("authorization", ""), "Bearer " + token
            )
        )
        return {"changes": service.changes(profile_id, since) if allowed else []}
    result = []
    for row in rows[:20]:
        if since and row["created_at"] < since:
            continue
        try:
            result.extend(
                dict(c, report_id=row["report_id"])
                for c in (await remote.get(row["report_id"]))["changes"]
            )
        except Exception:
            continue
    return {"changes": result[:200]}


@app.post("/v1/jobs", status_code=202)
async def submit(req: Request, identity=Depends(write_authorized)):
    job = await service.submit(req.model_dump(), identity)
    return dict(job, status_url="/v1/jobs/" + job["job_id"])


@app.get("/v1/jobs/{job_id}")
def job(job_id: str, identity=Depends(authorized)):
    result = service.get_job(job_id)
    if result["requested_by"] != identity:
        raise HTTPException(403, "Job belongs to another execution context")
    return result


@app.post("/v1/profiles")
def register(payload: dict, identity=Depends(write_authorized)):
    return service.register(payload)


@app.delete("/v1/jobs/{job_id}")
def cancel(job_id: str, identity=Depends(write_authorized)):
    result = service.get_job(job_id)
    if result["requested_by"] != identity:
        raise HTTPException(403, "Job belongs to another execution context")
    return service.cancel(job_id)


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!doctype html><html><head><meta charset="utf-8"><title>Horizon</title></head><body><h1>Horizon research</h1><p id="mode"></p><p>GitHub published reports are durable. Space jobs and local results are ephemeral. Coverage is bounded.</p><a href="/api-docs">API documentation</a><h2>Profiles</h2><select id="profiles"></select><h2>Reports and source coverage</h2><div id="reports"></div><h2>Authorized job status</h2><input id="job" placeholder="Job ID"><input id="token" type="password" placeholder="Agent token"><button id="check">Check</button><pre id="status"></pre><script>
fetch('/v1/info').then(r=>r.json()).then(i=>document.querySelector('#mode').textContent=i.remote_writes?'Authorized ephemeral execution enabled':'Read-only mode; remote execution disabled');
async function load(){let p=document.querySelector('#profiles').value;let r=await fetch('/v1/reports?profile_id='+encodeURIComponent(p)).then(r=>r.json());let box=document.querySelector('#reports');box.replaceChildren();for(let x of r.reports){let a=document.createElement('a');a.href='/v1/reports/'+encodeURIComponent(x.report_id);a.textContent=x.created_at+' '+x.status+' '+x.profile_id;box.append(a,document.createElement('br'));let d=await fetch(a.href).then(r=>r.json());let c=document.createElement('p');c.textContent='Search regions: '+(d.coverage?.regions||[]).join(', ')+'; missing: '+(d.coverage?.missing_regions||[]).join(', ');box.append(c);}}
fetch('/v1/profiles').then(r=>r.json()).then(r=>{let s=document.querySelector('#profiles');for(let p of r.profiles){let o=document.createElement('option');o.value=p.profile_id;o.textContent=p.name;s.append(o);}s.onchange=load;load();});
document.querySelector('#check').onclick=async()=>{let r=await fetch('/v1/jobs/'+encodeURIComponent(document.querySelector('#job').value),{headers:{Authorization:'Bearer '+document.querySelector('#token').value}});document.querySelector('#status').textContent=JSON.stringify(await r.json(),null,2);};
</script></body></html>"""
