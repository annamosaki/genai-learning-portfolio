#!/usr/bin/env python3
"""Edgar MCP with /health for Lambda Web Adapter readiness checks."""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    port = os.environ.get("PORT", os.environ.get("AWS_LWA_PORT", "8210"))
    host = os.environ.get("HOST", "0.0.0.0")
    identity = os.environ.get("EDGAR_IDENTITY", "Anna Mosaki mosakianna@gmail.com")
    os.environ.setdefault("EDGAR_IDENTITY", identity)

    # Prefer wrapping via Starlette if the package exposes an ASGI app;
    # otherwise exec the CLI (Lambda Web Adapter proxies to this process).
    try:
        from run_edgar_asgi import app  # type: ignore

        import uvicorn

        uvicorn.run(app, host=host, port=int(port), log_level="info")
        return
    except Exception:
        pass

    cmd = [
        "edgartools-mcp",
        "--transport",
        "streamable-http",
        "--host",
        host,
        "--port",
        str(port),
    ]
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
