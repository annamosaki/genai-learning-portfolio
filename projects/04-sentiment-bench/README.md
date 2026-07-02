# 05 — Verdict

Financial NLP benchmark: LSTM vs BERT vs FinBERT vs local LLM vs frontier.

## Metrics

Accuracy, macro-F1, ECE, latency, cost/1k, **downstream Sharpe**.

## Reproduce

```bash
pip install -r requirements.txt
python -m verdict.run_benchmark --smoke
```

Artifacts land in `content/artifacts/verdict/`.

## Live demo

`POST /api/verdict/classify` — cheap heuristic/FinBERT path with replay fallback.
