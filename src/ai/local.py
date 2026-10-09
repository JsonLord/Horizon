"""Deterministic native-pipeline fallback; never pretends to be an LLM."""

import os
from datetime import datetime, timezone
from bs4 import BeautifulSoup


def use_local(config):
    mode = os.getenv("HORIZON_AI_MODE", getattr(config, "mode", "auto"))
    if mode in ("local", "off"):
        return True
    if mode != "auto":
        raise ValueError("AI mode must be auto, local or off")
    key_name = getattr(config, "api_key_env", "")
    provider = getattr(config, "provider", None)
    return not os.getenv(key_name) and getattr(provider, "value", provider) != "ollama"


class LocalContentAnalyzer:
    async def analyze_batch(self, items):
        now = datetime.now(timezone.utc)
        for item in items:
            title = BeautifulSoup(item.title, "html.parser").get_text(" ", strip=True)[
                :500
            ]
            age = max(0, (now - item.published_at).total_seconds() / 3600)
            # Legacy ai_score carries a rules score; explicit metadata prevents model confusion.
            item.ai_score = round(5 + max(0, 3 * (1 - age / 168)), 3)
            item.ai_reason = "Deterministic relevance: 5 baseline + 0–3 recency over seven days; not importance, confidence or truth."
            item.ai_summary = title
            item.ai_tags = (
                [str(item.metadata["category"])]
                if item.metadata.get("category")
                else []
            )
            item.metadata.update(analysis_mode="deterministic", model_used=None)
        return items
