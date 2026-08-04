#!/usr/bin/env python3
"""Load OPENAI_API_KEY from Secrets Manager when OPENAI_SECRET_ARN is set, then exec CMD."""
from __future__ import annotations

import os
import sys


def main() -> None:
    arn = os.environ.get("OPENAI_SECRET_ARN", "").strip()
    if arn and not os.environ.get("OPENAI_API_KEY"):
        try:
            import boto3

            client = boto3.client("secretsmanager")
            resp = client.get_secret_value(SecretId=arn)
            secret = resp.get("SecretString") or ""
            if secret:
                os.environ["OPENAI_API_KEY"] = secret
        except Exception as exc:  # noqa: BLE001 - boot path must not crash loop
            print(f"warn: could not load OPENAI_SECRET_ARN: {exc}", file=sys.stderr)

    if len(sys.argv) < 2:
        print("usage: entrypoint.py <command> [args...]", file=sys.stderr)
        sys.exit(2)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
