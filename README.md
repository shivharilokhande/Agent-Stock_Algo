# AgentStockAlgo

NIFTY 500 swing + long-term scanner with an exit board for your own holdings.
**Recommendations only** — it never places orders. Fully separate from AgentAlgo
(own folder, own venv, own SQLite DB, port 8100; Kite is not used, so AgentAlgo's
broker session is never touched).

## Data
- Universe: NIFTY 500 constituents from niftyindices.com
- Prices: split/bonus-adjusted daily OHLCV via yfinance (`.NS`), 5 years, stored in
  `backend/data/agentstockalgo.db`. Incremental updates re-fetch a symbol's full history when a
  split/bonus re-adjusts it.

## Daily use (after ~18:00 IST)
```bash
cd backend
../.venv/bin/python scripts/run_scan.py          # update prices, scan, evaluate holdings
```
Edit `backend/data/holdings.json` with your positions (`symbol, qty, avg_price, buy_date,
horizon: swing|long`) to get HOLD / TIGHTEN / EXIT per holding.

## App (UI + API)
```bash
./run_app.sh            # then open http://localhost:8100
```
Pages: **Today** (breadth gauge + CONSIDER/WATCH signal cards), **Exits** (HOLD/TIGHTEN/EXIT board +
holdings editor), **Stock** (daily chart, EMA20/SMA50/SMA200, past backtest trades, today's
stop/target), **Backtest** (results by view and year, re-run button), **Settings** (gate, min PF,
slippage, delivery charges — stored in `backend/data/settings.json`).
The UI is plain ES modules in `frontend/` served by FastAPI — no npm build step (React + htm and
lightweight-charts load from esm.sh, so the browser needs internet).

## Research
```bash
../.venv/bin/python scripts/run_backtest.py      # writes docs/studies/YYYY-MM-DD-backtest.md
../.venv/bin/python -m pytest -q tests
```

## Setups
| Key | Horizon | Idea |
|---|---|---|
| PULLBACK_EMA20 | swing | uptrend, recently stretched ≥6% over EMA20, dips to it and closes green above (TREND_PB analogue) |
| BREAKOUT_55 | swing | 55-day high on ≥1.5× volume, strong close, ≤10% above EMA20 |
| RECLAIM_SMA50 | swing | closes back above SMA50 in a rising long-term trend (VWAP_RECLAIM analogue) |
| RSI2_DIP | swing | RSI(2) < 10 inside an uptrend, exit on close > SMA5 |
| TREND_TEMPLATE | long | 50>150>200 stack, near 52w high, RS top 30% |

Market gate: share of NIFTY 500 stocks above their own 50-day SMA ≥ 60%. Below that, signals are
shown as WATCH, never CONSIDER.

## Known limits
- Current-constituent universe → survivorship bias in the backtest (flatters results).
- Free Yahoo data is unofficial; verify prices with your broker before acting.
- No delivery % yet (planned: NSE bhavcopy), no fundamentals.
