# 03 — Research Digest

Personalized **literature, news & fund research** desk focused on time series applied to finance.
Free sources only: ArXiv API, curated RSS (AQR / Man / Two Sigma / Jane Street / Quantpedia / SSRN), optional Finnhub free tier. No newsletter.

## Demo

- Zone: [`/demos/research-digest`](http://localhost:3000/demos/research-digest)
- API: `http://localhost:8300/docs`

```bash
./start.sh --digest
```

## How it works

```
ArXiv + RSS (+ Finnhub?) + local seed
  → topic-weighted rank (topics.yaml)
  → Literature / News / Fund research / Watchlist
  → citation verify → artifact + SSE progress
```

1. Edit interests & feed URLs in [`topics.yaml`](topics.yaml)
2. Optional: set `FINNHUB_API_KEY` for free-tier market news (skipped if unset)
3. Run CLI or hit **Regenerate** in the demo

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
