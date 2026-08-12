# 03 — Research Digest

Personalized **literature, news & fund research** desk focused on time series applied to finance.
Free sources: ArXiv API, curated RSS, optional Finnhub. Optional Amazon SES newsletter for condensed digests.

## Demo

- Zone: [`/demos/research-digest`](http://localhost:3000/demos/research-digest)
- API: `http://localhost:8300/docs`

```bash
./start.sh --digest
```

## How it works

```
ArXiv + RSS (+ Finnhub?) + local seed
  → topic-weighted rank (topics.yaml + optional focus keywords)
  → Literature / News / Fund research / Watchlist
  → citation verify → artifact + SSE progress
  → optional SES newsletter to confirmed subscribers
```

1. Edit interests & feed URLs in [`topics.yaml`](topics.yaml)
2. Optional: set `FINNHUB_API_KEY` for free-tier market news (skipped if unset)
3. Enter a **Focus field / keywords** in the demo UI (or `--focus` on the CLI)
4. Run CLI or hit **Regenerate** in the demo — ArXiv queries + ranking steer toward that field
5. Optional: enter an email → **Subscribe** (confirm link) or **Email latest** for a one-shot condensed digest

## Newsletter (Amazon SES)

- From: `digest@annamosaki.com` (domain identity on `annamosaki.com`)
- Endpoints: `POST /api/newsletter/subscribe`, `GET /api/newsletter/confirm`, `POST /api/newsletter/send`, `POST /api/newsletter/send-one`
- After live regenerate, active subscribers receive the condensed HTML newsletter
- Weekday cron also calls `/api/newsletter/send` after refreshing the artifact

While SES is in sandbox, recipients must verify their address (Amazon sends a verification email) before delivery succeeds.

## Run

```bash
# CLI (writes content/artifacts/signal-desk/latest-review.json)
cd projects/03-research-digest
pip install -r requirements.txt
python -m signal_desk.run --once          # live fetch
python -m signal_desk.run --once --offline  # local JSONL only

# Dedicated API + web (from repo root)
honcho start digest-api digest-web
```

## Layout

```
projects/03-research-digest/
  topics.yaml
  signal_desk/          # pipeline + free source fetchers
  api/digest/           # FastAPI + SSE orchestrator (:8300)
  web/                  # Next multi-zone @digest/web (:3300)
  data/                 # local JSONL seed + inbox markdown
```

## Personalization

`topics.yaml` is the source of truth: topic weights (time-series × finance and quant research dominate), ArXiv queries, and RSS feed URLs. Unsupported / rumor items are dropped, not hedged.

## Keys (optional)

Nothing is required for a working local demo: ArXiv + RSS + local JSONL work without keys.

| Variable | Required? | Where to create |
|---|---|---|
| `FINNHUB_API_KEY` | Optional (live market news) | [Finnhub — free API key](https://finnhub.io/register) |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Optional (trace runs) | [Langfuse cloud](https://cloud.langfuse.com) → project → Settings → API Keys |
| `OPENAI_API_KEY` / etc. | Optional for other demos | Stored in AWS Secrets Manager `anna-portfolio/app-secrets` in production |

Local: put keys in repo-root `.env`. Production Digest Lambda loads `anna-portfolio/app-secrets` at boot.
