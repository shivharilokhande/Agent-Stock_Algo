"""Daily scan (run after the close): which NIFTY 500 stocks fired a setup on the latest bar,
each with entry reference, stop, target and the setup's backtest record (overall and on that stock).
Recommendations only - nothing here places an order."""
import json
from datetime import datetime

import numpy as np
import pandas as pd

from . import db, settings
from .backtest import build_features
from .config import BENCHMARK, BT_SUMMARY_FILE, BT_TRADES_FILE, NIFTY, SCAN_FILE
from .setups import POLICIES, SETUPS



def _r(x, n=2):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def load_backtest():
    if not BT_SUMMARY_FILE.exists():
        return {}, pd.DataFrame()
    summ = json.loads(BT_SUMMARY_FILE.read_text())
    by = {(r["setup"], r["policy"]): r for r in summ.get("results", [])}
    trades = pd.read_csv(BT_TRADES_FILE) if BT_TRADES_FILE.exists() else pd.DataFrame()
    return by, trades


def best_policy(setup, by, breadth_ok, MIN_TRADES=100):
    """Exit policy with the best breadth-matched profit factor (min trade count)."""
    key = "breadth_on" if breadth_ok else "breadth_off"
    best = None
    for pol in setup.policies:
        s = by.get((setup.key, pol), {}).get(key, {})
        if s.get("trades", 0) >= MIN_TRADES and (best is None or (s.get("pf") or 0) > (best[1].get("pf") or 0)):
            best = (pol, s)
    return best or (setup.policies[0], by.get((setup.key, setup.policies[0]), {}).get(key, {}))


def run(write=True):
    cfg = settings.get()
    BREADTH_ON, MIN_PF, MIN_TRADES = cfg["breadth_threshold_pct"] / 100, cfg["min_pf"], cfg["min_trades"]
    uni = db.load_universe().set_index("symbol")
    allp = db.load_prices()
    bench = allp.pop(BENCHMARK, None)
    allp.pop(NIFTY, None)
    prices = {s: d for s, d in allp.items() if s in uni.index}
    feats = build_features(prices, bench)
    last = max(f.index[-1] for f in feats.values())
    by, trades = load_backtest()
    any_f = next(f for f in feats.values() if f.index[-1] == last)
    breadth = float(any_f["breadth"].iat[-1])
    breadth_ok = breadth >= BREADTH_ON
    bench_ok = bool(any_f["regime"].iat[-1])
    cards = []
    for sym, f in feats.items():
        if f.index[-1] != last or len(f) < 260:
            continue
        for st in SETUPS:
            if not bool(st.signal(f).fillna(False).iat[-1]):
                continue
            pol, sstats = best_policy(st, by, breadth_ok, MIN_TRADES)
            close = float(f["close"].iat[-1])
            stop = float(st.stop(f).iat[-1])
            stop = min(stop, close * 0.99)
            risk = close - stop
            hist = trades[(trades.get("symbol") == sym) & (trades.get("setup") == st.key) &
                          (trades.get("policy") == pol) & (trades.get("status") == "CLOSED")] if len(trades) else trades
            pf = sstats.get("pf") or 0
            action = "CONSIDER" if (breadth_ok and pf >= MIN_PF and sstats.get("trades", 0) >= MIN_TRADES) else "WATCH"
            cards.append({
                "symbol": sym, "name": uni.at[sym, "name"], "industry": uni.at[sym, "industry"],
                "setup": st.key, "label": st.label, "horizon": st.horizon, "action": action,
                "exit_policy": pol, "exit_rule": POLICIES[pol]["desc"],
                "date": str(last.date()), "close": _r(close), "entry_note": "buy at next open; skip if it opens below the stop",
                "stop": _r(stop), "risk_pct": _r(risk / close * 100),
                "target": _r(close + 2 * risk) if pol == "R2" else None,
                "atr": _r(f["atr14"].iat[-1]), "ext_from_ema20_pct": _r(f["ext20"].iat[-1] * 100),
                "rs_pct": _r(f["rs_pct"].iat[-1] * 100, 0) if pd.notna(f["rs_pct"].iat[-1]) else None,
                "turnover_cr": _r(f["turnover_cr"].iat[-1], 1),
                "setup_backtest": sstats,
                "stock_history": {"trades": int(len(hist)),
                                  "win_pct": _r((hist["net_pnl"] > 0).mean() * 100, 0) if len(hist) else None,
                                  "avg_net_pct": _r(hist["net_pct"].mean()) if len(hist) else None},
            })
    order = {"CONSIDER": 0, "WATCH": 1}
    cards.sort(key=lambda c: (order[c["action"]], c["horizon"] != "swing", -(c["setup_backtest"].get("pf") or 0),
                              -(c["rs_pct"] or 0)))
    out = {"generated": datetime.now().isoformat(timespec="seconds"), "as_of": str(last.date()),
           "market": {"breadth_pct": round(breadth * 100, 1), "breadth_ok": breadth_ok,
                      "breadth_threshold_pct": int(BREADTH_ON * 100), "nifty500_above_200sma": bench_ok,
                      "note": ("Breadth healthy: swing setups have had an edge in this state." if breadth_ok else
                               "Breadth weak: swing setups lost money in this state in the backtest. Prefer to wait.")},
           "counts": {"stocks": len(feats), "signals": len(cards),
                      "consider": sum(c["action"] == "CONSIDER" for c in cards)},
           "signals": cards}
    if write:
        SCAN_FILE.write_text(json.dumps(out, indent=1, default=str))
    return out, feats
