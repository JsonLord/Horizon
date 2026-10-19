"""Inspect the real public Needle Router interface without inventing inference."""

from datetime import UTC, datetime
import hashlib
import ast
import re

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
                    result["reported_host"] = data.get("host")
                    files = [f.get("rfilename", "") for f in data.get("siblings", [])]
                    result["repository_files"] = files[:80]
                    result["source_interfaces"] = []
                    result["documented_interfaces"] = []
                    for name in ("README.md", "src/server.ts", "src/routes/systemOne.ts", "src/layaService.ts", "src/middleware/validation.ts", "src/utils/router.ts"):
                        if name not in files:
                            continue
                        try:
                            source = await client.get(f"{SPACE}/raw/{data['sha']}/{name}")
                            source.raise_for_status()
                            if len(source.content) > 250000:
                                continue
                            lines = []
                            for line in source.text.splitlines():
                                if re.search(r"process\.env|authorization|api[_-]?key|password|cookie|Bearer|https?://", line, re.I):
                                    continue
                                lines.append(line)
                            excerpt = "\n".join(lines)[:9000]
                            result["documented_interfaces"].append({"file": name, "sha256": hashlib.sha256(source.content).hexdigest(), "public_contract_excerpt": excerpt})
                        except Exception:
                            continue
                    selected = [f for f in files if f.endswith(".py") and re.fullmatch(r"[A-Za-z0-9_./-]+", f) and ".." not in f.split("/")][:8]
                    for name in selected:
                        try:
                            source = await client.get(f"{SPACE}/raw/{data['sha']}/{name}")
                            source.raise_for_status()
                            if len(source.content) > 250000:
                                continue
                            tree = ast.parse(source.text)
                            routes, models, keys = [], {}, set()
                            generative = False
                            for node in ast.walk(tree):
                                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    for decorator in node.decorator_list:
                                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr in ("get", "post", "route") and decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str) and decorator.args[0].value.startswith("/"):
                                            routes.append({"path": decorator.args[0].value, "method": decorator.func.attr, "function": node.name})
                                if isinstance(node, ast.ClassDef):
                                    fields = [n.target.id for n in node.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
                                    if fields:
                                        models[node.name] = fields
                                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                                    if node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) and re.fullmatch(r"[a-zA-Z_]{1,64}", node.args[0].value):
                                        keys.add(node.args[0].value)
                                    if "completions.create" in ast.unparse(node.func) or "generate_content" in ast.unparse(node.func):
                                        generative = True
                            result["source_interfaces"].append({"file": name, "sha256": hashlib.sha256(source.content).hexdigest(), "routes": routes, "models": models, "request_keys": sorted(keys), "contains_generative_client_call": generative})
                        except Exception:
                            continue
            except Exception as exc:
                result["observations"].append({"url": url, "error": "HTTP_" + str(exc.response.status_code) if isinstance(exc, httpx.HTTPStatusError) else "network_or_contract_unavailable"})
        native = {}
        for path in ("/health", "/ready", "/v1/info", "/v1/gates/route"):
            try:
                response = await client.get(HOST + path)
                result["observations"].append({"url": HOST + path, "http_status": response.status_code})
                if response.status_code == 200 and len(response.content) < 50000:
                    data = response.json()
                    if path == "/v1/info":
                        native.update(service=data.get("service"), inference_endpoint=data.get("inference_endpoint"), model=data.get("backends", {}).get("laya", {}).get("model"), capabilities=data.get("capabilities"), generative=data.get("backends", {}).get("laya", {}).get("generative"))
                    if path == "/ready":
                        native["ready"] = data.get("backends", {}).get("laya", {}).get("ready") is True
            except Exception:
                result["observations"].append({"url": HOST + path, "error": "network_or_contract_unavailable"})
        result["native_contract"] = native
        if native.get("service") == "system-one" and native.get("inference_endpoint") == "/v1/system-one" and native.get("model") == "receptron/laya-onnx" and "score" in (native.get("capabilities") or []):
            result["native_contract_verified"] = True
            result["status"] = "native_structured_classifier_discovered_not_yet_inferred"
        return result
    finally:
        if own:
            await client.aclose()
