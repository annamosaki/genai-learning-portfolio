#!/usr/bin/env python3
"""Load secrets from Secrets Manager, then exec CMD.

Supports:
  OPENAI_SECRET_ARN  → plain string → OPENAI_API_KEY
  APP_SECRETS_ARN    → JSON object → env keys (FINNHUB_API_KEY, OPENAI_API_KEY, …)
"""
from __future__ import annotations

import json
import os
import sys


def _load_secret_string(arn: str) -> str:
    import boto3

    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=arn)
    return resp.get("SecretString") or ""


def main() -> None:
    app_arn = os.environ.get("APP_SECRETS_ARN", "").strip()
    if app_arn:
        try:
            raw = _load_secret_string(app_arn)
            data = json.loads(raw) if raw.startswith("{") else {}
            if isinstance(data, dict):
                for key, value in data.items():
                    if not key or value is None:
                        continue
                    val = str(value).strip()
                    if not val or val.startswith("PLACEHOLDER"):
                        continue
                    # Do not overwrite an already-injected env var.
                    if not os.environ.get(key):
                        os.environ[key] = val
        except Exception as exc:  # noqa: BLE001
            print(f"warn: could not load APP_SECRETS_ARN: {exc}", file=sys.stderr)

    openai_arn = os.environ.get("OPENAI_SECRET_ARN", "").strip()
    if openai_arn and not os.environ.get("OPENAI_API_KEY"):
        try:
            secret = _load_secret_string(openai_arn)
            if secret and not secret.startswith("PLACEHOLDER"):
                os.environ["OPENAI_API_KEY"] = secret
        except Exception as exc:  # noqa: BLE001
            print(f"warn: could not load OPENAI_SECRET_ARN: {exc}", file=sys.stderr)

    if len(sys.argv) < 2:
        print("usage: entrypoint.py <command> [args...]", file=sys.stderr)
        sys.exit(2)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
