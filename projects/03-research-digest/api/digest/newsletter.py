"""Newsletter subscribe + SES delivery for Research Digest."""

from __future__ import annotations

import hashlib
import html
import os
import re
import secrets
import time
from email.utils import parseaddr
from typing import Any, Optional

from .serverless_runtime import is_serverless


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _from_address() -> str:
    return (
        os.environ.get("NEWSLETTER_FROM")
        or "Research Digest <digest@annamosaki.com>"
    ).strip()


def _public_base() -> str:
    return (
        os.environ.get("DIGEST_PUBLIC_URL")
        or "https://digest.annamosaki.com/demos/research-digest"
    ).rstrip("/")


def _api_base() -> str:
    return (
        os.environ.get("DIGEST_API_PUBLIC_URL")
        or "https://digest-api.annamosaki.com"
    ).rstrip("/")


def normalize_email(raw: str) -> str:
    _, addr = parseaddr((raw or "").strip())
    addr = addr.lower().strip()
    if not addr or not EMAIL_RE.match(addr):
        raise ValueError("Invalid email address")
    return addr


def _token() -> str:
    return secrets.token_urlsafe(24)


def _sub_pk(email: str) -> str:
    return f"sub#{email}"


def _active_pk() -> str:
    return "subs#active"


class SubscriberStore:
    """Persist subscribers in DynamoDB (RUNS_TABLE) or a local JSON fallback."""

    def __init__(self) -> None:
        self.table_name = (
            os.environ.get("SUBSCRIBERS_TABLE")
            or os.environ.get("RUNS_TABLE")
            or ""
        ).strip()
        self._table = None
        self._local_path = None
        if not self.table_name:
            from pathlib import Path

            root = Path(__file__).resolve().parents[4]
            path = root / "content" / "artifacts" / "signal-desk" / "subscribers.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            self._local_path = path

    @property
    def mode(self) -> str:
        return "dynamodb" if self.table_name else "local"

    def _get_table(self):
        if self._table is None:
            import boto3

            self._table = boto3.resource("dynamodb").Table(self.table_name)
        return self._table

    def _local_load(self) -> dict[str, Any]:
        assert self._local_path is not None
        if not self._local_path.exists():
            return {"by_email": {}, "active": []}
        import json

        return json.loads(self._local_path.read_text())

    def _local_save(self, data: dict[str, Any]) -> None:
        assert self._local_path is not None
        import json

        self._local_path.write_text(json.dumps(data, indent=2))

    def get(self, email: str) -> Optional[dict[str, Any]]:
        email = email.lower()
        if self.table_name:
            resp = self._get_table().get_item(Key={"pk": _sub_pk(email), "sk": "meta"})
            item = resp.get("Item")
            if not item:
                return None
            raw = item.get("data")
            if isinstance(raw, str):
                import json

                return json.loads(raw)
            return raw  # type: ignore[return-value]
        return self._local_load().get("by_email", {}).get(email)

    def put(self, record: dict[str, Any]) -> None:
        email = record["email"]
        if self.table_name:
            import json

            self._get_table().put_item(
                Item={
                    "pk": _sub_pk(email),
                    "sk": "meta",
                    "data": json.dumps(record, default=str),
                    # Keep subscribers; refresh a far-future ttl marker for table hygiene only if present.
                    "ttl": int(time.time()) + 86400 * 3650,
                }
            )
            if record.get("status") == "active":
                self._get_table().put_item(
                    Item={
                        "pk": _active_pk(),
                        "sk": email,
                        "data": json.dumps({"email": email}, default=str),
                        "ttl": int(time.time()) + 86400 * 3650,
                    }
                )
            else:
                self._get_table().delete_item(Key={"pk": _active_pk(), "sk": email})
            return

        data = self._local_load()
        data.setdefault("by_email", {})[email] = record
        active = set(data.get("active") or [])
        if record.get("status") == "active":
            active.add(email)
        else:
            active.discard(email)
        data["active"] = sorted(active)
        self._local_save(data)

    def list_active(self) -> list[dict[str, Any]]:
        if self.table_name:
            from boto3.dynamodb.conditions import Key

            resp = self._get_table().query(
                KeyConditionExpression=Key("pk").eq(_active_pk()),
            )
            emails = [i["sk"] for i in resp.get("Items", [])]
            out = []
            for email in emails:
                rec = self.get(email)
                if rec and rec.get("status") == "active":
                    out.append(rec)
            return out

        data = self._local_load()
        return [
            data["by_email"][e]
            for e in data.get("active", [])
            if e in data.get("by_email", {})
        ]


subscriber_store = SubscriberStore()


def subscribe(email: str) -> dict[str, Any]:
    email = normalize_email(email)
    existing = subscriber_store.get(email)
    if existing and existing.get("status") == "active":
        return {"email": email, "status": "active", "message": "Already subscribed."}

    token = _token()
    record = {
        "email": email,
        "status": "pending",
        "confirm_token": token,
        "unsub_token": _token(),
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    if existing and existing.get("unsub_token"):
        record["unsub_token"] = existing["unsub_token"]
    subscriber_store.put(record)

    confirm_url = f"{_api_base()}/api/newsletter/confirm?token={token}&email={email}"
    subject = "Confirm your Research Digest subscription"
    body_text = (
        "Confirm your subscription to Anna Mosaki's Research Digest.\n\n"
        f"Confirm: {confirm_url}\n\n"
        "If you did not request this, ignore this email."
    )
    body_html = f"""
    <div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;color:#111">
      <h1 style="font-size:22px">Confirm subscription</h1>
      <p>You're one click away from condensed literature, news, and fund-research digests.</p>
      <p><a href="{html.escape(confirm_url)}" style="background:#0b7;color:#04110c;padding:10px 16px;border-radius:999px;text-decoration:none;font-weight:600">Confirm email</a></p>
      <p style="color:#666;font-size:12px">If you did not request this, ignore this email.</p>
    </div>
    """
    send_result = send_email(to=email, subject=subject, text=body_text, html=body_html)
    return {
        "email": email,
        "status": "pending",
        "message": "Check your inbox to confirm.",
        "delivery": send_result,
    }


def confirm(email: str, token: str) -> dict[str, Any]:
    email = normalize_email(email)
    rec = subscriber_store.get(email)
    if not rec or rec.get("confirm_token") != token:
        raise ValueError("Invalid or expired confirmation link")
    rec["status"] = "active"
    rec["confirmed_at"] = int(time.time())
    rec["updated_at"] = int(time.time())
    subscriber_store.put(rec)
    return {"email": email, "status": "active", "message": "Subscription confirmed."}


def unsubscribe(email: str, token: str) -> dict[str, Any]:
    email = normalize_email(email)
    rec = subscriber_store.get(email)
    if not rec or rec.get("unsub_token") != token:
        raise ValueError("Invalid unsubscribe link")
    rec["status"] = "unsubscribed"
    rec["updated_at"] = int(time.time())
    subscriber_store.put(rec)
    return {"email": email, "status": "unsubscribed", "message": "You are unsubscribed."}


def render_newsletter(review: dict[str, Any]) -> tuple[str, str, str]:
    """Return (subject, text, html) condensed newsletter for a review artifact."""
    date = review.get("date") or "today"
    focus = review.get("focus_query") or review.get("lede") or "Time series × finance"
    subject = f"Research Digest — {date}"
    sections = review.get("sections") or []

    def paras_for(heading: str) -> list[dict[str, Any]]:
        for s in sections:
            if s.get("heading") == heading:
                return list(s.get("paragraphs") or [])[:5]
        return []

    lines = [f"Research Digest — {date}", f"Focus: {focus}", ""]
    blocks_html = []

    for heading, label in (
        ("Literature", "Papers"),
        ("News", "News"),
        ("Fund research", "Fund research"),
    ):
        paras = paras_for(heading)
        lines.append(label.upper())
        items_html = []
        if not paras:
            lines.append("  (no items)")
        for p in paras:
            cite = (p.get("citations") or [{}])[0]
            title = cite.get("title") or (p.get("text") or "").split(" — ")[0]
            url = cite.get("url") or ""
            snippet = ""
            text = p.get("text") or ""
            if " — " in text:
                snippet = text.split(" — ", 1)[1][:180]
            lines.append(f"  • {title}")
            if url:
                lines.append(f"    {url}")
            if snippet:
                lines.append(f"    {snippet}")
            link = (
                f'<a href="{html.escape(url)}" style="color:#0a7;text-decoration:none">{html.escape(title)}</a>'
                if url
                else html.escape(title)
            )
            items_html.append(
                f"<li style='margin:0 0 12px'>{link}"
                + (f"<div style='color:#555;font-size:13px;margin-top:4px'>{html.escape(snippet)}</div>" if snippet else "")
                + "</li>"
            )
        lines.append("")
        blocks_html.append(
            f"<h2 style='font-size:16px;margin:24px 0 8px;border-bottom:1px solid #ddd;padding-bottom:6px'>{html.escape(label)}</h2>"
            f"<ul style='padding-left:18px;margin:0'>{''.join(items_html) or '<li style=\"color:#888\">No items</li>'}</ul>"
        )

    demo = _public_base()
    lines.append(f"Open the desk: {demo}")
    text = "\n".join(lines)
    html_body = f"""
    <div style="font-family:Georgia,serif;max-width:640px;margin:0 auto;color:#111;line-height:1.45">
      <p style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#888">Project 03 · Research Digest</p>
      <h1 style="font-size:26px;margin:8px 0 4px">Reading desk — {html.escape(str(date))}</h1>
      <p style="color:#444;margin:0 0 8px">{html.escape(str(focus)[:280])}</p>
      {''.join(blocks_html)}
      <p style="margin-top:28px"><a href="{html.escape(demo)}" style="color:#0a7">Open Research Digest →</a></p>
    </div>
    """
    return subject, text, html_body


def send_email(*, to: str, subject: str, text: str, html: str) -> dict[str, Any]:
    """Send via Amazon SES. In dry-run/local without credentials, write a preview file."""
    from_addr = _from_address()
    # Local / missing AWS: write preview instead of failing hard
    if not is_serverless() and not os.environ.get("AWS_ACCESS_KEY_ID") and not os.environ.get("AWS_PROFILE"):
        # Still try boto3 default chain (aws login credentials)
        pass

    try:
        import boto3

        client = boto3.client("sesv2", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        client.send_email(
            FromEmailAddress=from_addr,
            Destination={"ToAddresses": [to]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text, "Charset": "UTF-8"},
                        "Html": {"Data": html, "Charset": "UTF-8"},
                    },
                }
            },
        )
        return {"ok": True, "provider": "ses", "to": to}
    except Exception as exc:  # noqa: BLE001
        # Persist a local preview so demos still work offline
        try:
            from pathlib import Path

            root = Path(__file__).resolve().parents[4]
            preview_dir = root / "content" / "artifacts" / "signal-desk" / "mail-preview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha1(f"{to}:{subject}:{time.time()}".encode()).hexdigest()[:10]
            (preview_dir / f"{digest}.html").write_text(html)
            (preview_dir / f"{digest}.txt").write_text(text)
        except Exception:
            pass
        return {"ok": False, "provider": "ses", "to": to, "error": str(exc)[:300]}


def dispatch_newsletter(review: dict[str, Any]) -> dict[str, Any]:
    subject, text, html_body = render_newsletter(review)
    active = subscriber_store.list_active()
    results = []
    for rec in active:
        email = rec["email"]
        unsub = f"{_api_base()}/api/newsletter/unsubscribe?token={rec.get('unsub_token')}&email={email}"
        html_with_footer = (
            html_body
            + f"<p style='margin-top:32px;font-size:12px;color:#888'>"
            + f"<a href='{html.escape(unsub)}' style='color:#888'>Unsubscribe</a></p>"
        )
        text_with_footer = text + f"\n\nUnsubscribe: {unsub}\n"
        results.append(
            send_email(to=email, subject=subject, text=text_with_footer, html=html_with_footer)
        )
    ok = sum(1 for r in results if r.get("ok"))
    return {
        "ok": True,
        "subscribers": len(active),
        "sent": ok,
        "failed": len(results) - ok,
        "results": results[:20],
        "store": subscriber_store.mode,
    }


def send_one_shot(email: str, review: dict[str, Any]) -> dict[str, Any]:
    email = normalize_email(email)
    subject, text, html_body = render_newsletter(review)
    delivery = send_email(to=email, subject=subject, text=text, html=html_body)
    return {"email": email, "delivery": delivery}
