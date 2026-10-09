"""Bounded public GitHub archive consumer; no write identity assumed."""

import os
import re
import time

import httpx

from .reporting import Report


class RemoteArchive:
    def __init__(self):
        repo = os.getenv("HORIZON_ARCHIVE_REPO", "JsonLord/Horizon")
        ref = os.getenv("HORIZON_ARCHIVE_REF", "intel")
        if not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo
        ) or not re.fullmatch(r"[A-Za-z0-9_-]+", ref):
            raise ValueError("Invalid archive binding")
        self.base = f"https://raw.githubusercontent.com/{repo}/{ref}/"
        self.cache = {}
        self.status = "unchecked"

    async def read(self, path):
        if not re.fullmatch(r"intel/[a-zA-Z0-9_./-]+", path) or ".." in path.split("/"):
            raise ValueError("Unsafe archive path")
        if path in self.cache and time.monotonic() - self.cache[path][0] < 60:
            return self.cache[path][1]
        async with httpx.AsyncClient(timeout=10) as client:
            async with client.stream("GET", self.base + path) as response:
                response.raise_for_status()
                data = b""
                async for chunk in response.aiter_bytes():
                    data += chunk
                    if len(data) > 1_000_000:
                        raise ValueError("Archive too large")
        import json

        if len(self.cache) >= 32:
            oldest = min(self.cache, key=lambda k: self.cache[k][0])
            del self.cache[oldest]
        value = json.loads(data)
        self.cache[path] = (time.monotonic(), value)
        self.status = "connected"
        return value

    async def list(self, profile_id=None, limit=20, offset=0):
        try:
            index = await self.read("intel/manifest.json")
            rows = index["reports"][:100]
            return [r for r in rows if not profile_id or r["profile_id"] == profile_id][
                offset : offset + limit
            ]
        except Exception:
            self.status = "unavailable"
            return None

    async def get(self, rid):
        rows = await self.list(limit=100)
        row = next((r for r in rows or [] if r["report_id"] == rid), None)
        if not row:
            raise KeyError("Published report not found")
        report = Report.model_validate(await self.read(row["path"])).model_dump()
        if report["report_id"] != rid:
            raise ValueError("Archive identity mismatch")
        report["links"].update(
            published_json=self.base + row["path"],
            published_markdown=self.base
            + row["path"].replace("/report.json", "/report.md"),
        )
        return report
