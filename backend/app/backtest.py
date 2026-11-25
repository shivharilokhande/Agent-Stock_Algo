"""No-lookahead daily backtest.

Rules
- Signal on bar i's close -> enter at bar i+1's OPEN (+slippage). Skip if that open is at/below the stop.
- Intraday: low <= stop -> stopped (at the open if it gapped below); high >= target -> target
  (at the open if it gapped above). Both on one bar -> stop (conservative).
- Close-based exits (SMA5 / SMA150) fill at the NEXT open. Time exits fill at that bar's close.
- One open position per stock per setup+policy; the next signal is taken only after the exit.
- Net P&L includes delivery charges on TRADE_NOTIONAL and slippage both sides.
"""
import numpy as np
import pandas as pd

from . import charges
from .config import MIN_RISK_PCT, SLIPPAGE_PCT, TRADE_NOTIONAL
from .indicators import features, market_breadth, rs_percentile
from .setups import BREADTH_ON, POLICIES, SETUPS


def simulate(f, i, stop0, policy):
    """Simulate one trade from signal bar i. Returns dict or None (not entered)."""
    p = POLICIES[policy]
    n = len(f)
    j0 = i + 1
    if j0 >= n:
        return None
    o, h, l, c = (f[k].values for k in ("open", "high", "low", "close"))
    slip = SLIPPAGE_PCT / 100
    entry = o[j0] * (1 + slip)
    if not np.isfinite(entry) or not np.isfinite(stop0) or o[j0] <= stop0:
        return None
    stop0 = min(stop0, entry * (1 - MIN_RISK_PCT / 100))
    risk = entry - stop0
    target = entry + p["target_r"] * risk if "target_r" in p else None
    atr = f["atr14"].values
    sma5 = f["sma5"].values
    sma150 = f["sma150"].values
    stop, hc = stop0, entry
    exit_idx = exit_px = reason = None

    for j in range(j0, n):
        if l[j] <= stop:
            exit_idx, reason = j, ("STOP" if stop <= stop0 else "TRAIL")
            exit_px = min(o[j], stop) if j > j0 else stop
            break
        if target is not None and h[j] >= target:
            exit_idx, reason = j, "TARGET"
            exit_px = max(o[j], target) if j > j0 else target
            break
        held = j - j0 + 1
        if policy == "MA5" and c[j] > sma5[j]:
            if j + 1 < n:
                exit_idx, exit_px, reason = j + 1, o[j + 1], "MA5"
            break
        if policy == "LONG" and c[j] < sma150[j]:
            if j + 1 < n:
                exit_idx, exit_px, reason = j + 1, o[j + 1], "SMA150"
            break
        if held >= p["max_days"]:
            exit_idx, exit_px, reason = j, c[j], "TIME"
            break
        if policy == "TRAIL":
            hc = max(hc, c[j])
            stop = max(stop, hc - p["trail_atr"] * atr[j])

    idx = f.index
    tr = {"signal_date": idx[i], "entry_date": idx[j0], "entry": entry, "stop0": stop0,
          "target": target, "regime": bool(f["regime"].iat[i]), "rs_pct": f["rs_pct"].iat[i],
          "breadth": f["breadth"].iat[i] if "breadth" in f else np.nan}
    if exit_idx is None:                          # still open at the end of data
        mark = c[-1] * (1 - slip)
        tr.update(status="OPEN", exit_date=idx[-1], exit=mark, reason="OPEN", exit_idx=n - 1)
    else:
        tr.update(status="CLOSED", exit_date=idx[exit_idx], exit=exit_px * (1 - slip),
                  reason=reason, exit_idx=exit_idx)
    qty = TRADE_NOTIONAL / entry
    buy, sell = TRADE_NOTIONAL, qty * tr["exit"]
    cost = charges.round_trip(buy, sell)
    tr["gross_pct"] = (sell / buy - 1) * 100
    tr["net_pnl"] = sell - buy - cost
    tr["net_pct"] = tr["net_pnl"] / buy * 100
    tr["charges"] = cost
    tr["net_r"] = tr["net_pnl"] / (qty * risk)
    tr["days"] = int(np.busday_count(idx[j0].date(), tr["exit_date"].date())) + 1
    return tr


def build_features(prices, bench):
    bench_close = bench["close"] if bench is not None else None
    rs = rs_percentile(prices)
    br = market_breadth(prices)
    return {s: features(df, bench_close, rs[s] if s in rs else None, br) for s, df in prices.items()}


def run(prices, bench, setups=None, feats=None, log=None):
    """prices: {symbol: df}. Returns DataFrame of trades (closed and open)."""
    setups = setups or SETUPS
    feats = feats or build_features(prices, bench)
    rows = []
    for k, (sym, f) in enumerate(feats.items()):
        if len(f) < 260:
            continue
        valid = f["sma200"].notna() & f["atr14"].notna() & f["sma200_up"].notna()
        for st in setups:
            sig = (st.signal(f).fillna(False) & valid).values
            stops = st.stop(f).values
            idxs = np.flatnonzero(sig)
            for pol in st.policies:
                next_free = 0
                for i in idxs:
                    if i < next_free:
                        continue
                    tr = simulate(f, i, stops[i], pol)
                    if tr is None:
                        continue
                    tr.update(symbol=sym, setup=st.key, policy=pol, horizon=st.horizon)
                    rows.append(tr)
                    next_free = tr["exit_idx"] + 1
        if log and (k + 1) % 100 == 0:
            log(f"  backtested {k + 1}/{len(feats)} symbols")
    return pd.DataFrame(rows)


def stats(t):
    """Per-trade statistics on CLOSED trades."""
    t = t[t["status"] == "CLOSED"] if "status" in t else t
    n = len(t)
    if n == 0:
        return {"trades": 0}
    wins = t[t["net_pnl"] > 0]
    gain, loss = wins["net_pnl"].sum(), -t.loc[t["net_pnl"] <= 0, "net_pnl"].sum()
    streak = best = 0
    for v in t.sort_values("exit_date")["net_pnl"]:
        streak = streak + 1 if v <= 0 else 0
        best = max(best, streak)
    return {
        "trades": int(n),
        "win_pct": round(len(wins) / n * 100, 1),
        "avg_net_pct": round(t["net_pct"].mean(), 2),
        "median_net_pct": round(t["net_pct"].median(), 2),
        "avg_win_pct": round(wins["net_pct"].mean(), 2) if len(wins) else 0.0,
        "avg_loss_pct": round(t.loc[t["net_pnl"] <= 0, "net_pct"].mean(), 2) if n > len(wins) else 0.0,
        "pf": round(gain / loss, 2) if loss > 0 else None,
        "avg_net_r": round(t["net_r"].mean(), 2),
        "avg_days": round(t["days"].mean(), 1),
        "avg_charges": round(t["charges"].mean(), 0),
        "gross_avg_pct": round(t["gross_pct"].mean(), 2),
        "max_loss_streak": int(best),
        "pct_per_day": round(t["net_pct"].sum() / max(t["days"].sum(), 1), 3),
    }


def summarize(trades):
    """Nested summary per setup+policy: all / regime on / regime off / halves / years."""
    out = []
    if trades.empty:
        return out
    closed = trades[trades["status"] == "CLOSED"].copy()
    if closed.empty:
        return out
    split = closed["signal_date"].quantile(0.6)
    for (setup, pol), g in closed.groupby(["setup", "policy"]):
        row = {"setup": setup, "policy": pol, "horizon": g["horizon"].iat[0],
               "all": stats(g),
               "regime_on": stats(g[g["regime"]]),
               "regime_off": stats(g[~g["regime"]]),
               "breadth_on": stats(g[g["breadth"] >= BREADTH_ON]),
               "breadth_off": stats(g[~(g["breadth"] >= BREADTH_ON)]),
               "breadth_on_last_40": stats(g[(g["breadth"] >= BREADTH_ON) & (g["signal_date"] > split)]),
               "breadth_off_last_40": stats(g[~(g["breadth"] >= BREADTH_ON) & (g["signal_date"] > split)]),
               "first_60": stats(g[g["signal_date"] <= split]),
               "last_40": stats(g[g["signal_date"] > split]),
               "by_year": {str(y): stats(gy) for y, gy in g.groupby(g["signal_date"].dt.year)},
               "exits": g["reason"].value_counts().to_dict(),
               "open_now": int(((trades["setup"] == setup) & (trades["policy"] == pol) &
                                (trades["status"] == "OPEN")).sum())}
        out.append(row)
    return out
