import asyncio

import httpx
import pytest

from src.research.branches import resolve, validate_ref


@pytest.mark.parametrize("ref", ["evil", "refs/pull/1/head", "main;echo", "../main", "https://evil.test/repo", "feature/unapproved", "$(echo)"])
def test_unapproved_refs_are_rejected(ref):
    with pytest.raises(ValueError):
        validate_ref(ref)


def test_pin_same_repository_head(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "JsonLord/Horizon")
    sha = "a" * 40
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"sha": sha}))) as client:
            assert (await resolve("main", "JsonLord/Horizon", client))["sha"] == sha
            assert (await resolve(sha, "JsonLord/Horizon", client))["ref"] == "main"
            with pytest.raises(ValueError, match="Cross-repository"):
                await resolve("main", "other/repo", client)
            with pytest.raises(ValueError, match="not the head"):
                await resolve("b" * 40, "JsonLord/Horizon", client)
    asyncio.run(run())
