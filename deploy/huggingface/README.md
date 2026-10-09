---
title: Horizon Research
sdk: docker
app_port: 7860
---

# Horizon Research

Prepared README for the actual Hugging Face Docker Space checkout. This file does not identify or create a Space. Copy it as the Space's root README together with the repository's Dockerfile, pyproject.toml, uv.lock, src/, profiles/, schemas/, and data/config.example.json through an authorized deployment mechanism.

The dashboard is public and read-only by default. Remote execution requires the separately configured HORIZON_AGENT_TOKEN. Local jobs are ephemeral; GitHub's intel branch is the durable archive. HF authentication does not provide GitHub Actions' job token. Port 7860 and UID 1000 only; CPU hardware suffices.
