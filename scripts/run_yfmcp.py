#!/usr/bin/env python3
"""Run Yahoo Finance MCP (yfmcp) with a /health endpoint for the status page."""

from __future__ import annotations

import os

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse

from yfmcp.server import mcp

PORT = int(os.environ.get("YFMCP_PORT", os.environ.get("MCP_YFINANCE_PORT", "8211")))
HOST = os.environ.get("YFMCP_HOST", "127.0.0.1")

mcp.settings.host = HOST
mcp.settings.port = PORT
mcp.settings.log_level = os.environ.get("YFMCP_LOG_LEVEL", "INFO")

# The SDK only allows localhost Host headers unless told otherwise.
# CloudFront calls this as yf.annamosaki.com, which otherwise returns 421.
_security = getattr(mcp.settings, "transport_security", None)
if _security is not None:
    if hasattr(_security, "enable_dns_rebinding_protection"):
        _security.enable_dns_rebinding_protection = False
    _hosts = list(getattr(_security, "allowed_hosts", []) or [])
    for _host in (
        "yf.annamosaki.com",
        "yf.annamosaki.com:*",
        "*.lambda-url.us-east-1.on.aws",
        "*.lambda-url.us-east-1.on.aws:*",
    ):
        if _host not in _hosts:
            _hosts.append(_host)
    _security.allowed_hosts = _hosts
    _origins = list(getattr(_security, "allowed_origins", []) or [])
    for _origin in (
        "https://yf.annamosaki.com",
        "https://annamosaki.com",
        "https://www.annamosaki.com",
        "https://desk.annamosaki.com",
        "https://lab.annamosaki.com",
    ):
        if _origin not in _origins:
            _origins.append(_origin)
    _security.allowed_origins = _origins


async def health(_request):
    return JSONResponse(
        {
            "status": "healthy",
            "mcp": "yfmcp",
            "name": "Yahoo Finance MCP",
            "transport": "streamable-http",
            "path": "/mcp",
        }
    )


# Use the MCP app itself so its lifespan starts the session manager.
# Mounting it under another Starlette left that task group uninitialized.
app = mcp.streamable_http_app()
app.router.routes.append(Route("/health", health))

if __name__ == "__main__":
    print(f"Starting yfmcp on http://{HOST}:{PORT} (MCP /mcp, health /health)", flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
