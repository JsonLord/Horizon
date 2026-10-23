"""Resolve only approved same-repository branch heads to immutable revisions."""

import json
import os
import re
from urllib.parse import quote

import httpx

from .profiles import ROOT


def policy():
    return json.loads((ROOT / "config/program-automation.json").read_text())


def validate_ref(ref):
    if not isinstance(ref, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,127}", ref) or ".." in ref:
        raise ValueError("Invalid research revision")
    if ref not in policy()["allowed_refs"] and not re.fullmatch(r"[a-f0-9]{40}", ref):
        raise ValueError("Research ref is not approved")
    return ref


async def resolve(ref, repository, client=None):
    validate_ref(ref)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository binding")
    bound = os.getenv("GITHUB_REPOSITORY", "JsonLord/Horizon")
    if repository != bound:
        raise ValueError("Cross-repository research is forbidden")
    own = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        refs = [ref] if ref in policy()["allowed_refs"] else policy()["allowed_refs"]
        for approved in refs:
            response = await client.get(f"https://api.github.com/repos/{repository}/commits/{quote(approved, safe='')}", headers=headers)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            sha = response.json().get("sha", "")
            if not re.fullmatch(r"[a-f0-9]{40}", sha):
                raise ValueError("GitHub returned an invalid revision")
            if ref == approved or ref == sha:
                return {"ref": approved, "sha": sha, "repository": repository}
        raise ValueError("Revision is not the head of an approved same-repository branch")
    finally:
        if own:
            await client.aclose()
