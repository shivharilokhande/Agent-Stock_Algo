"""Entry and exit plan for a signal, matching the backtested rules.

Entry  : buy at the next session's open (that is what the backtest did). The size is set on the
         signal close. "Do not pay above" = the price at which risk per share is 1.5x the planned
         risk; above it the trade no longer fits the plan (guidance, not part of the backtest).
         Skip it if the open is at or below the stop.
Exit   : depends on the setup's exit rule (R2 / TRAIL / MA5 / LONG), with today's levels.
"""
import numpy as np
import pandas as pd

from .setups import POLICIES

MAX_RISK_MULT = 1.5


def _r(x, n=2):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def busday_add(day, n):
    return str(np.busday_offset(pd.Timestamp(day).date(), n, roll="forward"))


def size(entry, stop, cfg):
    risk_ps = entry - stop
    if risk_ps <= 0:
        return {"qty": 0, "risk_amount": 0, "position_value": 0}
    budget = cfg["capital"] * cfg["risk_pct"] / 100
    qty = int(budget // risk_ps)
    cap_qty = int((cfg["capital"] * cfg["max_position_pct"] / 100) // entry)
    capped = qty > cap_qty
    qty = min(qty, cap_qty)
    return {"qty": qty, "risk_amount": _r(qty * risk_ps, 0), "position_value": _r(qty * entry, 0),
            "capped_by_position_limit": capped, "risk_budget": _r(budget, 0)}


def build(f, policy, stop, cfg):
    """f: features frame of one stock (last row = signal day). Returns the plan dict."""
    last = f.iloc[-1]
    day = f.index[-1]
    close = float(last["close"])
    atr = float(last["atr14"])
    stop = float(min(stop, close * 0.99))
    risk = close - stop
    p = POLICIES[policy]
    entry = {
        "how": "Buy at the next open",
        "ref_price": _r(close),
        "max_price": _r(stop + MAX_RISK_MULT * risk),
        "skip_if_open_below": _r(stop),
        "note": f"Sized on the close. Above the max price the risk per share is over {MAX_RISK_MULT}x plan",
    }
    exit_ = {"stop": _r(stop), "stop_pct": _r(-risk / close * 100), "rule": policy, "rule_text": p["desc"],
             "levels": [], "exit_by": busday_add(day, p["max_days"]) if p["max_days"] < 500 else None}
    lv = exit_["levels"]
    lv.append({"label": "Stop loss", "price": _r(stop), "pct": _r(-risk / close * 100),
               "when": "Exit if the price trades at or below it"})
    if policy == "R2":
        tgt = close + p["target_r"] * risk
        exit_["target"] = _r(tgt)
        lv.append({"label": "Target (2R)", "price": _r(tgt), "pct": _r((tgt / close - 1) * 100),
                   "when": "Exit the whole position when it trades here"})
        lv.append({"label": "Time exit", "price": None, "pct": None,
                   "when": f"Exit at the close on {exit_['exit_by']} if neither level is hit"})
    elif policy == "TRAIL":
        mult = p["trail_atr"]
        lv.append({"label": "Trailing stop", "price": None, "pct": None,
                   "when": f"Each close, move the stop up to highest close since entry − {mult:g}×ATR "
                           f"(today {mult:g}×ATR = {atr * mult:,.2f}); never move it down"})
        for r in (2, 3):
            lvl = close + r * risk
            lv.append({"label": f"{r}R level", "price": _r(lvl), "pct": _r((lvl / close - 1) * 100),
                       "when": "Reference only: the trail decides the exit, not this level"})
        lv.append({"label": "Time exit", "price": None, "pct": None,
                   "when": f"Exit at the close on {exit_['exit_by']} if the trail has not closed it"})
    elif policy == "MA5":
        lv.append({"label": "Exit signal", "price": _r(last["sma5"]), "pct": _r((last["sma5"] / close - 1) * 100),
                   "when": "Sell at the next open after a close above the 5-day average (today's value shown)"})
        lv.append({"label": "Time exit", "price": None, "pct": None,
                   "when": f"Exit at the close on {exit_['exit_by']} at the latest"})
    elif policy == "LONG":
        lv.append({"label": "Trend exit", "price": _r(last["sma150"]), "pct": _r((last["sma150"] / close - 1) * 100),
                   "when": "Sell at the next open after a close below the 150-day average (rises over time)"})
    return {"entry": entry, "exit": exit_, "size": size(close, stop, cfg), "atr": _r(atr)}
