"""Bounded GitHub REST access using the caller's existing GitHub identity."""

import asyncio
import base64
import json
import os
import re
import shutil
from urllib.parse import quote

import httpx


class ControlError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details


class GitHub:
    def __init__(self, repo=None, client=None, token=None):
        self.repo = repo or os.getenv("HORIZON_GITHUB_REPO", "JsonLord/Horizon")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repo):
            raise ValueError("Invalid GitHub repository")
        self.client = client
        self.token = (
            token
            if token is not None
            else os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        )
        self.prefix = f"repos/{self.repo}/"
        self._auth_checked = bool(self.token)
        self.cache = {}

    async def authenticate(self, required=False):
        if not self._auth_checked:
            self._auth_checked = True
            if shutil.which("gh"):
                process = await asyncio.create_subprocess_exec(
                    "gh",
                    "auth",
                    "token",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                try:
                    output, _ = await asyncio.wait_for(process.communicate(), 10)
                except TimeoutError:
                    process.kill()
                    await process.communicate()
                else:
                    if process.returncode == 0:
                        self.token = output.decode().strip()
        if required and not self.token:
            raise ControlError(
                "GITHUB_AUTH_REQUIRED",
                "Use existing GitHub CLI login or GH_TOKEN/GITHUB_TOKEN. Dispatch needs Actions write; proposals need contents/pull-requests/workflow write access. Do not supply a new Horizon token.",
            )

    async def request(self, method, path, payload=None, params=None, missing=False):
        if not path.startswith(self.prefix):
            raise ValueError("GitHub request outside configured repository")
        await self.authenticate(required=method != "GET")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        client = self.client or httpx.AsyncClient(timeout=25)
        try:
            for attempt in range(3 if method == "GET" else 1):
                try:
                    async with client.stream(
                        method,
                        "https://api.github.com/" + path,
                        json=payload,
                        params=params,
                        headers=headers,
                    ) as response:
                        if (
                            method == "GET"
                            and response.status_code in (429, 502, 503, 504)
                            and attempt < 2
                        ):
                            await asyncio.sleep(0.5 * 2**attempt)
                            continue
                        if response.status_code == 404 and missing:
                            return None
                        if response.status_code >= 400:
                            status = response.status_code
                            if method != "GET" and status >= 500:
                                raise ControlError(
                                    "GITHUB_WRITE_UNCERTAIN",
                                    "GitHub failed during a write. Reconcile correlated run/branch/PR state before retrying.",
                                    {"status": status},
                                )
                            code = {
                                401: "GITHUB_AUTH_REQUIRED",
                                403: "GITHUB_FORBIDDEN",
                                404: "GITHUB_NOT_FOUND",
                                409: "GITHUB_CONFLICT",
                                422: "GITHUB_INVALID_OR_CONFLICT",
                                429: "GITHUB_RATE_LIMITED",
                            }.get(status, "GITHUB_API_ERROR")
                            hint = (
                                "Check GitHub permissions and branch/workflow policies."
                                if status in (401, 403)
                                else "Check the selected repository/ref, input validation, and concurrent proposals; retry after resolving the cause."
                            )
                            raise ControlError(
                                code,
                                f"GitHub returned HTTP {status}. {hint}",
                                {"status": status},
                            )
                        data = b""
                        async for chunk in response.aiter_bytes():
                            data += chunk
                            if len(data) > 5_000_000:
                                raise ControlError(
                                    "GITHUB_RESPONSE_TOO_LARGE",
                                    "GitHub response exceeds the controller limit.",
                                )
                        return json.loads(data) if data else {}
                except httpx.TransportError as exc:
                    if method == "GET" and attempt < 2:
                        await asyncio.sleep(0.5 * 2**attempt)
                        continue
                    raise ControlError(
                        "GITHUB_WRITE_UNCERTAIN"
                        if method != "GET"
                        else "GITHUB_UNAVAILABLE",
                        "GitHub response was not received. Check correlated state before retrying a write; do not blindly dispatch again.",
                    ) from exc
        finally:
            if self.client is None:
                await client.aclose()

    async def get(self, suffix, params=None, missing=False):
        return await self.request(
            "GET", self.prefix + suffix, params=params, missing=missing
        )

    async def write(self, method, suffix, payload):
        return await self.request(method, self.prefix + suffix, payload=payload)

    async def commit(self, ref):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/\-]{0,127}", ref) or ".." in ref:
            raise ValueError("Invalid Git revision")
        result = await self.get("commits/" + quote(ref, safe=""))
        if not re.fullmatch(r"[a-f0-9]{40}", result.get("sha", "")):
            raise ControlError(
                "GITHUB_INVALID_RESPONSE", "GitHub returned no valid source commit."
            )
        return result

    async def file(self, path, ref, missing=False):
        if ".." in path.split("/") or not re.fullmatch(r"[a-zA-Z0-9_./\-]+", path):
            raise ValueError("Unsafe repository path")
        key = (path, ref)
        if re.fullmatch(r"[a-f0-9]{40}", ref) and key in self.cache:
            return self.cache[key]
        result = await self.get("contents/" + path, {"ref": ref}, missing=missing)
        if result is None:
            return None
        if (
            not isinstance(result, dict)
            or result.get("type") != "file"
            or result.get("encoding") != "base64"
            or result.get("size", 1_000_001) > 1_000_000
        ):
            raise ControlError(
                "GITHUB_INVALID_FILE", "Expected a bounded ordinary repository file."
            )
        try:
            data = base64.b64decode(result["content"], validate=False)
        except Exception as exc:
            raise ControlError("GITHUB_INVALID_FILE", "Invalid file encoding.") from exc
        if len(data) > 1_000_000:
            raise ControlError(
                "GITHUB_INVALID_FILE", "Repository file exceeds the size ceiling."
            )
        if len(self.cache) >= 256:
            self.cache.pop(next(iter(self.cache)))
        if re.fullmatch(r"[a-f0-9]{40}", ref):
            self.cache[key] = data
        return data
