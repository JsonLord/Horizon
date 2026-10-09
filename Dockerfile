FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY profiles ./profiles
COPY schemas ./schemas
COPY data/config.example.json ./data/config.example.json
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then UV_NATIVE_TLS=true SSL_CERT_FILE=/run/secrets/build_ca uv sync --frozen --no-dev; else uv sync --frozen --no-dev; fi && useradd -m -u 1000 horizon && chown -R horizon:horizon /app
USER 1000
ENV PYTHONUNBUFFERED=1 HORIZON_CREDENTIAL_FREE=true HORIZON_AI_MODE=auto HORIZON_ARCHIVE_REPO=JsonLord/Horizon HORIZON_ARCHIVE_REF=intel HORIZON_MAX_JOBS=2 UV_CACHE_DIR=/tmp/uv-cache
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=3s CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health',timeout=2)"]
ENTRYPOINT ["/app/.venv/bin/python", "-m"]
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "7860"]
