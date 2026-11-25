"""Exit board: HOLD / TIGHTEN / EXIT for your own holdings (data/holdings.json).

holdings.json: [{"symbol": "TCS", "qty": 10, "avg_price": 3500, "buy_date": "2026-10-01",
                 "horizon": "swing" | "long"}]
Swing rules mirror the TRAIL exit (initial stop 2xATR under cost, then 3xATR chandelier off the
highest close since purchase). Long rules mirror the LONG exit (15% stop, close below SMA150).
"""
import json
from datetime import datetime

import pandas as pd

from .config import EXITS_FILE, HOLDINGS_FILE
from . import settings

EXAMPLE = [{"symbol": "RELIANCE", "qty": 10, "avg_price": 1300, "buy_date": "2026-10-01", "horizon": "long"}]


def load_holdings():
    if not HOLDINGS_FILE.exists():
        HOLDINGS_FILE.write_text(json.dumps(EXAMPLE, indent=1))
    return json.loads(HOLDINGS_FILE.read_text())


def evaluate(h, f):
    sym = h["symbol"].upper()
    cost = float(h["avg_price"])
    horizon = h.get("horizon", "swing")
    bd = pd.Timestamp(h.get("buy_date") or f.index[-60])
    since = f[f.index >= bd]
    if since.empty:
        since = f.iloc[-1:]
    row = f.iloc[-1]
    close = float(row["close"])
    atr = float(row["atr14"])
    pnl_pct = (close / cost - 1) * 100
    reasons, action = [], "HOLD"

    if horizon == "long":
        stop = cost * 0.85
        if close <= stop:
            action = "EXIT"; reasons.append(f"close {close:.2f} is at/below the 15% stop {stop:.2f}")
        if close < row["sma150"]:
            action = "EXIT"; reasons.append(f"closed below SMA150 ({row['sma150']:.2f})")
        if action != "EXIT":
            if close < row["sma50"]:
                action = "TIGHTEN"; reasons.append(f"below SMA50 ({row['sma50']:.2f})")
            if pd.notna(row["rs_pct"]) and row["rs_pct"] < 0.5:
                action = "TIGHTEN"; reasons.append(f"relative strength fell to {row['rs_pct'] * 100:.0f}th percentile")
            if close < 0.75 * row["hi252"]:
                action = "TIGHTEN"; reasons.append("more than 25% below its 52-week high")
        stop_level = max(stop, float(row["sma150"]))
    else:
        atr_at_buy = float(since["atr14"].iat[0]) if pd.notna(since["atr14"].iat[0]) else atr
        init = cost - 2 * atr_at_buy
        chandelier = float(since["close"].max()) - 3 * atr
        stop_level = max(init, chandelier)
        if close <= stop_level:
            action = "EXIT"; reasons.append(f"close {close:.2f} at/below trailing stop {stop_level:.2f}")
        else:
            if close - stop_level < atr:
                action = "TIGHTEN"; reasons.append("within 1 ATR of the trailing stop")
            if close < row["ema20"]:
                action = "TIGHTEN"; reasons.append(f"closed below 20 EMA ({row['ema20']:.2f})")
            risk = cost - init
            if risk > 0 and close - cost >= 2 * risk:
                action = "TIGHTEN"; reasons.append("up 2R or more: consider booking part")
        held = len(since)
        if held >= 60 and action == "HOLD":
            action = "TIGHTEN"; reasons.append(f"held {held} sessions (swing time limit 60)")
    if pd.notna(row.get("breadth")) and row["breadth"] < settings.breadth_on() and action == "HOLD":
        reasons.append("market breadth weak: no new adds")
    return {"symbol": sym, "horizon": horizon, "qty": h.get("qty"), "avg_price": cost, "close": round(close, 2),
            "pnl_pct": round(pnl_pct, 2), "action": action, "stop_level": round(stop_level, 2),
            "reasons": reasons or ["trend intact"], "date": str(f.index[-1].date())}


def run(feats, write=True):
    out = []
    for h in load_holdings():
        f = feats.get(h["symbol"].upper())
        if f is None:
            out.append({"symbol": h["symbol"], "action": "UNKNOWN", "reasons": ["not in NIFTY 500 data"]})
            continue
        out.append(evaluate(h, f))
    order = {"EXIT": 0, "TIGHTEN": 1, "HOLD": 2, "UNKNOWN": 3}
    out.sort(key=lambda r: order.get(r["action"], 9))
    doc = {"generated": datetime.now().isoformat(timespec="seconds"), "holdings": out}
    if write:
        EXITS_FILE.write_text(json.dumps(doc, indent=1, default=str))
    return doc
