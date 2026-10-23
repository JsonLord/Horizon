import asyncio
import hashlib
import json

import httpx
import pytest

from src.research.programs.laya import SemanticFit, classify, public_input
from src.research.programs.model_contract import HOST
from src.research.programs.relevance import DIMENSIONS, Policy, load_policy, score
from src.research.reporting import dumps
from tests.test_program_verification import NOW, check


def record():
    return check('<h1>AI software startup accelerator</h1><p>Applications are open</p><a href="/apply">Apply</a><p>Deadline: 2026-12-01</p><p>Eligibility: software founders and entrepreneurs.</p><p>Equity-free funding, mentoring, workspace and founder networking. No fee.</p>')


def test_weighted_heuristic_and_eligibility_are_not_probabilities():
    p = load_policy()
    r = record()
    result = score(r, p, now=NOW)
    assert result.fit_score == round(sum(p.weights[k] * result.dimensions[k] for k in p.weights), 4)
    assert result.probability_relevant is None and result.calibration_status == "uncalibrated"
    assert result.hard_eligibility == "eligible"
    r.application_status = "unknown"
    result = score(r, p, now=NOW)
    assert result.decision == "review"
    r.application_status = "closed"
    assert score(r, p, now=NOW).decision == "not_prioritized"


def test_policy_rejects_fake_calibration_and_bad_weights():
    data = load_policy().model_dump()
    data["weights"]["strategic_fit"] = 3
    with pytest.raises(ValueError):
        Policy.model_validate(data)
    data = load_policy().model_dump()
    data["calibration"]["status"] = "calibrated"
    with pytest.raises(ValueError):
        Policy.model_validate(data)


@pytest.mark.parametrize("kind", ["valid", "bad_citation", "bad_range", "wrong_hash", "timeout", "routing_only"])
def test_optional_inference_contract_and_safe_fallback(kind):
    p = load_policy()
    r = record()
    r.legacy = {"private_profile": "MUST_NOT_LEAVE_PROCESS"}
    dto = public_input(r, p)
    digest = hashlib.sha256(dumps(dto).encode()).hexdigest()
    assert "MUST_NOT_LEAVE_PROCESS" not in dumps(dto)
    def respond(request):
        assert "MUST_NOT_LEAVE_PROCESS" not in request.content.decode()
        assert request.url.path == "/v1/system-one"
        if kind == "timeout":
            raise httpx.ReadTimeout("bounded")
        sent = json.loads(request.content)
        assert sent["state"]["input_hash"] == digest
        answers = {}
        for key, question in sent["questions"].items():
            if question["type"] == "score":
                answers[key] = {"type": "score", "score": 2.4, "legend": {str(i): name for i, name in enumerate(question["criteria"])}, "confidence": .8}
            else:
                answers[key] = {"type": "choice", "choice": next(iter(question["criteria"]))}
        if kind == "bad_citation": answers["citation"]["choice"] = "invented"
        if kind == "bad_range": answers["benefits"]["score"] = 4
        return httpx.Response(200, json={"request_id": digest if kind != "wrong_hash" else "0" * 64, "model": "receptron/laya-onnx", "backend": "laya", "results": answers})
    contract = {"native_contract_verified": kind != "routing_only", "native_contract": {"ready": True, "model": "receptron/laya-onnx"}}
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await classify(r, p, contract, client)
    semantic, metadata = asyncio.run(run())
    assert bool(semantic) == (kind == "valid")
    assert metadata["inference_succeeded"] == (kind == "valid")
    assert metadata["fallback"] == (None if kind == "valid" else "deterministic")
    if semantic:
        assert all(abs(v - .8) < 1e-8 for v in semantic.dimensions.values())


def test_no_key_or_unavailable_endpoint_never_fabricates_inference():
    semantic, metadata = asyncio.run(classify(record(), load_policy(), {}))
    assert semantic is None and metadata["status"] == "model_unavailable"


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_transient_model_failures_are_bounded_and_keep_hard_filters(status, monkeypatch):
    calls = []
    async def no_wait(seconds):pass
    monkeypatch.setattr('src.research.programs.laya.asyncio.sleep', no_wait)
    def respond(request):
        calls.append(request.headers['X-Request-ID'])
        return httpx.Response(status, text='PRIVATE UPSTREAM BODY')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await classify(record(), load_policy(), {'native_contract_verified':True,'native_contract':{'ready':True,'model':'receptron/laya-onnx'}},client)
    semantic, metadata = asyncio.run(run())
    assert semantic is None and metadata['fallback']=='deterministic'
    assert metadata['attempts']==3 and len(set(calls))==1
    assert 'PRIVATE' not in json.dumps(metadata)
    r=record();r.application_status='closed'
    boosted=SemanticFit(policy_version=load_policy().policy_version,input_hash='a'*64,model_identity='receptron/laya-onnx',dimensions={k:1 for k in DIMENSIONS},reason_codes=[],unknowns=[],cited_evidence_ids=[r.source_evidence[0].evidence_id])
    assert score(r,load_policy(),boosted,now=NOW).hard_eligibility=='ineligible'
