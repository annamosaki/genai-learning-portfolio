#!/usr/bin/env python3
"""Run Yahoo Finance MCP (yfmcp) with a /health endpoint for the status page."""

from __future__ import annotations

import os

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse

from yfmcp.server import mcp

PORT = int(os.environ.get("YFMCP_PORT", os.environ.get("MCP_YFINANCE_PORT", "8211")))
HOST = os.environ.get("YFMCP_HOST", "127.0.0.1")

mcp.settings.host = HOST
mcp.settings.port = PORT
mcp.settings.log_level = os.environ.get("YFMCP_LOG_LEVEL", "INFO")


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


app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app()),
    ]
)

if __name__ == "__main__":
    print(f"Starting yfmcp on http://{HOST}:{PORT} (MCP /mcp, health /health)", flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
