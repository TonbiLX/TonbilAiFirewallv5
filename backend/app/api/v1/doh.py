# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DNS-over-HTTPS (DoH) endpoint — RFC 8484 uyumlu.
# Browser/OS DoH istemcilerinden gelen sorgulari dns_proxy handler'ina iletir.

import base64
import logging

from fastapi import APIRouter, Request, Response

from app.workers.dns_proxy import handle_doh_query, get_doh_context

logger = logging.getLogger("tonbilai.doh")

router = APIRouter()

_DOH_CONTENT_TYPE = "application/dns-message"


def _get_client_ip(request: Request) -> str:
    """Client IP: X-Real-IP (nginx) veya dogrudan."""
    return (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "0.0.0.0")
    )


@router.post("/dns-query")
async def doh_post(request: Request):
    """RFC 8484 — POST /dns-query (application/dns-message body)."""
    content_type = request.headers.get("content-type", "")
    if "dns-message" not in content_type:
        return Response(status_code=415, content="Unsupported Media Type")

    dns_wire = await request.body()
    if not dns_wire or len(dns_wire) < 12:
        return Response(status_code=400, content="Invalid DNS message")

    redis_client, stats, query_log = get_doh_context()
    if redis_client is None or stats is None or query_log is None:
        return Response(status_code=503, content="DoH not initialized")

    client_ip = _get_client_ip(request)
    response = await handle_doh_query(dns_wire, client_ip, redis_client, stats, query_log)

    if not response:
        return Response(status_code=502, content="Upstream failure")

    return Response(content=response, media_type=_DOH_CONTENT_TYPE)


@router.get("/dns-query")
async def doh_get(request: Request, dns: str = ""):
    """RFC 8484 — GET /dns-query?dns=<base64url> ."""
    if not dns:
        return Response(status_code=400, content="Missing dns parameter")

    try:
        # base64url decode (padding otomatik)
        padded = dns + "=" * (4 - len(dns) % 4) if len(dns) % 4 else dns
        dns_wire = base64.urlsafe_b64decode(padded)
    except Exception:
        return Response(status_code=400, content="Invalid base64url encoding")

    if len(dns_wire) < 12:
        return Response(status_code=400, content="Invalid DNS message")

    redis_client, stats, query_log = get_doh_context()
    if redis_client is None or stats is None or query_log is None:
        return Response(status_code=503, content="DoH not initialized")

    client_ip = _get_client_ip(request)
    response = await handle_doh_query(dns_wire, client_ip, redis_client, stats, query_log)

    if not response:
        return Response(status_code=502, content="Upstream failure")

    return Response(content=response, media_type=_DOH_CONTENT_TYPE)
