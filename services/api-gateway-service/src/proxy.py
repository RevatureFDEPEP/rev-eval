"""Translate a downstream httpx response into the gateway's response.

The gateway is a pass-through: the status code, body bytes and content type a
service returns are what the client receives. The body is never parsed, so an
empty 204, a plain-text error or an invalid JSON body cannot turn into a
gateway 500.
"""
from __future__ import annotations

import httpx
from fastapi.responses import Response

# Hop-by-hop headers (RFC 9110 section 7.6.1) and headers that describe the
# upstream encoding rather than the body we send. httpx has already decoded
# any content-encoding, and Starlette sets content-length for the new body.
# CORS and request-id headers are owned by the gateway's own middleware.
_DROPPED_RESPONSE_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "content-encoding",
        "date",
        "server",
        "x-request-id",
        "access-control-allow-origin",
        "access-control-allow-credentials",
        "access-control-allow-methods",
        "access-control-allow-headers",
        "access-control-expose-headers",
        "access-control-max-age",
    }
)

# Statuses that must not carry a body (RFC 9110 sections 15.3.5, 15.4.5).
_NO_BODY_STATUSES = frozenset({204, 304})


def build_proxy_response(resp: httpx.Response) -> Response:
    """Return a Starlette response mirroring ``resp`` without parsing its body."""
    headers = [
        (name, value)
        for name, value in resp.headers.multi_items()
        if name.lower() not in _DROPPED_RESPONSE_HEADERS
    ]

    if resp.status_code in _NO_BODY_STATUSES or 100 <= resp.status_code < 200:
        response = Response(status_code=resp.status_code)
        # Starlette adds content-length: 0 for an empty body; a 204/304 must
        # not carry one, and the content type of an absent body is meaningless.
        for name, value in headers:
            if name.lower() != "content-type":
                response.headers.append(name, value)
        if "content-length" in response.headers:
            del response.headers["content-length"]
        return response

    response = Response(content=resp.content, status_code=resp.status_code)
    for name, value in headers:
        response.headers.append(name, value)
    return response
