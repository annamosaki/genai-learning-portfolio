# 06 — Horizon

Time-series foundation models on **returns & realised volatility** (not price levels).

## Models

Baselines: seasonal naive, ARIMA/ETS, LightGBM, N-HiTS, PatchTST  
TSFMs: TimesFM 2.5, Chronos-2, Moirai 2.0, TiRex

## Methodology

- Purged walk-forward + embargo (Lopez de Prado)
- Probabilistic metrics: CRPS, pinball
- Pretraining contamination split
- Vol-targeted Sharpe as decision metric

## Reproduce

```bash
pip install -r requirements.txt
python -m horizon.run_benchmark --smoke
```
