import asyncio
import json
import httpx
import pytest
from src.research.analyzers import enrich


def test_optional_endpoint_without_key_and_validation(monkeypatch):
    monkeypatch.setenv("HORIZON_LLM_BASE_URL", "https://model.example.org/v1")
    monkeypatch.setenv("HORIZON_LLM_MODEL", "fixture-model")
    monkeypatch.delenv("HORIZON_LLM_API_KEY", raising=False)
    original = httpx.AsyncClient
    observed = []

    def response(req):
        observed.append(req)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"finding_ids": ["evidence-id"]})
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(response), **kw),
    )
    findings = [{"finding_id": "evidence-id", "summary": "Fixture title"}]
    result = asyncio.run(enrich(findings))
    assert result[:2] == ("fixture-model", "model_evidence_selection")
    assert "authorization" not in observed[0].headers
    assert findings[0]["summary"] == "Fixture title"
    assert findings[0]["model_selected"] is True
    observed.clear()
    assert asyncio.run(enrich(findings, "off"))[:2] == (None, "deterministic")
    assert not observed


def test_invalid_model_claim_falls_back(monkeypatch):
    monkeypatch.setenv("HORIZON_LLM_BASE_URL", "https://model.example.org/v1")
    monkeypatch.setenv("HORIZON_LLM_MODEL", "fixture-model")
    original = httpx.AsyncClient

    def response(req):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"finding_ids":["invented"]}'}}]
            },
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(response), **kw),
    )
    assert asyncio.run(enrich([{"finding_id": "real", "summary": "Fixture evidence"}]))[
        :2
    ] == (None, "deterministic")


@pytest.mark.parametrize('status',[429,500,502,503])
def test_openai_compatible_transient_errors_have_bounded_checkpoint_safe_fallback(monkeypatch,status):
    monkeypatch.setenv('HORIZON_LLM_BASE_URL','https://model.example.org/v1')
    monkeypatch.setenv('HORIZON_LLM_MODEL','fixture-model')
    original=httpx.AsyncClient
    seen=[]
    async def no_wait(seconds):pass
    monkeypatch.setattr('src.research.analyzers.asyncio.sleep',no_wait)
    def respond(request):
        seen.append(request.content)
        return httpx.Response(status,text='PRIVATE PROVIDER BODY')
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    findings=[{'finding_id':'existing-id','summary':'Public title'}]
    before=json.dumps(findings)
    result=asyncio.run(enrich(findings))
    assert result[:2]==(None,'deterministic')
    assert len(seen)==3 and len(set(seen))==1
    assert json.dumps(findings)==before
    assert 'PRIVATE' not in json.dumps(result)
