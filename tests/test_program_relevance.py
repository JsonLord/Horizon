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
    p.laya.inference_endpoint, p.laya.model = HOST + "/v1/chat/completions", "verified-model"
    r = record()
    r.legacy = {"private_profile": "MUST_NOT_LEAVE_PROCESS"}
    dto = public_input(r, p)
    digest = hashlib.sha256(dumps(dto).encode()).hexdigest()
    assert "MUST_NOT_LEAVE_PROCESS" not in dumps(dto)
    def respond(request):
        assert "MUST_NOT_LEAVE_PROCESS" not in request.content.decode()
        if kind == "timeout":
            raise httpx.ReadTimeout("bounded")
        value = {"policy_version": p.policy_version, "input_hash": digest, "model_identity": "verified-model", "dimensions": {k: .8 for k in DIMENSIONS}, "reason_codes": ["software_fit"], "unknowns": [], "cited_evidence_ids": [r.source_evidence[0].evidence_id]}
        if kind == "bad_citation": value["cited_evidence_ids"] = ["invented"]
        if kind == "bad_range": value["dimensions"]["benefits"] = 2
        if kind == "wrong_hash": value["input_hash"] = "0" * 64
        return httpx.Response(200, json={"model": "verified-model", "choices": [{"message": {"content": json.dumps(value)}}]})
    contract = {"paths": {"/v1/chat/completions": {"post": {}}}} if kind != "routing_only" else {"paths": {"/v1/gates/route": {"post": {}}}}
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await classify(r, p, contract, client)
    semantic, metadata = asyncio.run(run())
    assert bool(semantic) == (kind == "valid")
    assert metadata["inference_succeeded"] == (kind == "valid")
    assert metadata["fallback"] == (None if kind == "valid" else "deterministic")


def test_no_key_or_unavailable_endpoint_never_fabricates_inference():
    semantic, metadata = asyncio.run(classify(record(), load_policy(), {}))
    assert semantic is None and metadata["status"] == "model_unavailable"
