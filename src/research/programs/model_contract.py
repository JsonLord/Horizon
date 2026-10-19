"""Inspect the real public Needle Router interface without inventing inference."""

from datetime import UTC, datetime
import hashlib

import httpx


SPACE = "https://huggingface.co/spaces/Leon4gr45/needle-router"
HOST = "https://leon4gr45-needle-router.hf.space"


async def inspect_contract(client=None):
    own = client is None
    client = client or httpx.AsyncClient(timeout=15, follow_redirects=False)
    result = {"space": SPACE, "observed_at": datetime.now(UTC).isoformat(), "inference_succeeded": False, "status": "model_unavailable", "observations": []}
    try:
        for url in ("https://huggingface.co/api/spaces/Leon4gr45/needle-router", HOST + "/openapi.json"):
            try:
                response = await client.get(url)
                entry = {"url": url, "http_status": response.status_code}
                result["observations"].append(entry)
                response.raise_for_status()
                if len(response.content) > 1_000_000:
                    raise ValueError("model_contract_too_large")
                data = response.json()
                if url.endswith("openapi.json"):
                    result["openapi_sha256"] = hashlib.sha256(response.content).hexdigest()
                    result["paths"] = {}
                    for path, methods in data.get("paths", {}).items():
                        if any(word in path.lower() for word in ("route", "classif", "complet", "infer", "model", "health")):
                            result["paths"][path] = {method: {k: spec.get(k) for k in ("summary", "requestBody", "responses") if k in spec} for method, spec in methods.items() if method in ("get", "post")}
                    result["schemas"] = data.get("components", {}).get("schemas", {})
                    result["status"] = "contract_discovered_inference_not_verified"
                else:
                    result["space_sha"] = data.get("sha")
                    result["runtime_stage"] = data.get("runtime", {}).get("stage")
            except Exception as exc:
                result["observations"].append({"url": url, "error": "HTTP_" + str(exc.response.status_code) if isinstance(exc, httpx.HTTPStatusError) else "network_or_contract_unavailable"})
        return result
    finally:
        if own:
            await client.aclose()
