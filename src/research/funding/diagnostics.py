"""Read-only HEAD diagnostics for the fixed, operator-reviewed funding registry.

No redirects are followed, no bodies or credentials are saved, and this does not
replace the DNS/robots/SSRF guards used by Horizon's collection path.
"""

import os
import re
import socket
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from .models import AccessCheck
from ..profiles import safe_url


def classify(http_status, connect_status):
    if connect_status and connect_status >= 400:
        return "proxy_path"
    if http_status and http_status < 400:
        return "none"
    return "unknown"  # Server/Via alone cannot prove who generated a refusal.


def diagnose(source):
    url = safe_url(source["url"])
    host = urlsplit(url).hostname
    if not any(host == d or host.endswith("." + d) for d in source["official_domains"]):
        raise ValueError("Diagnostics require a registered official URL")
    try:
        local_dns = bool(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
    except socket.gaierror:
        local_dns = False
    with tempfile.TemporaryDirectory(prefix="horizon-head-") as temp:
        headers = Path(temp) / "headers"
        result = subprocess.run(["curl", "--head", "--silent", "--max-time", "20", "--max-redirs", "0", "--dump-header", str(headers), "--output", os.devnull, "--write-out", "%{http_code}|%{http_connect}", url], capture_output=True, text=True, timeout=25)
        values = result.stdout.split("|")
        status, connect = [int(v) or None for v in values] if len(values) == 2 and all(v.isdigit() for v in values) else (None, None)
        # Keep final response headers only. Exclude cookies, authorization,
        # request IDs, signed locations and arbitrary vendor text.
        blocks = re.split(r"\r?\n\r?\n", headers.read_text() if headers.exists() else "")
        final = next((b for b in reversed(blocks) if b.startswith("HTTP/")), "")
        allowed = {"content-type", "date", "server", "via", "retry-after", "x-cache", "x-envoy-upstream-service-time"}
        response_headers = {k.lower(): v.strip()[:500] for line in final.splitlines()[1:] if ":" in line for k, v in [line.split(":", 1)] if k.lower() in allowed}
        return AccessCheck(observed_at=datetime.now(UTC), method="HEAD", url=url, http_status=status, proxy_connect_status=connect, proxy_configured=bool(os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")), local_dns_resolves=local_dns, response_headers=response_headers, redirect_chain_complete=status not in (301, 302, 303, 307, 308), failure_origin=classify(status, connect), collector_limitation=None if local_dns else "local_dns_unavailable")
