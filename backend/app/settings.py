"""App settings editable from the Settings page (stored in data/settings.json, not in code)."""
import copy
import json

from .config import CHARGES, DATA, SLIPPAGE_PCT

FILE = DATA / "settings.json"

DEFAULTS = {
    "breadth_threshold_pct": 60,   # market gate: % of NIFTY 500 above their own 50-day SMA
    "min_pf": 1.2,                 # setup's breadth-matched backtest PF needed for CONSIDER
    "min_trades": 100,             # ...with at least this many backtest trades
    "slippage_pct": SLIPPAGE_PCT,  # per side
    "capital": 200000,             # Rs used to size positions
    "risk_pct": 1.0,               # % of capital you accept losing if the stop is hit
    "max_position_pct": 25.0,      # cap on one position as % of capital
    "charges": dict(CHARGES),
}

LIMITS = {
    "breadth_threshold_pct": (0, 100), "min_pf": (0.5, 5), "min_trades": (0, 10000),
    "slippage_pct": (0, 2), "capital": (1000, 1e9), "risk_pct": (0.1, 5), "max_position_pct": (1, 100),
}


def get():
    s = copy.deepcopy(DEFAULTS)
    if FILE.exists():
        try:
            saved = json.loads(FILE.read_text())
            s.update({k: v for k, v in saved.items() if k in s and k != "charges"})
            s["charges"].update({k: v for k, v in saved.get("charges", {}).items() if k in s["charges"]})
        except (ValueError, OSError):
            pass
    return s


def save(new):
    s = get()
    for k, (lo, hi) in LIMITS.items():
        if k in new:
            v = float(new[k])
            if not lo <= v <= hi:
                raise ValueError(f"{k} must be between {lo} and {hi}")
            s[k] = int(v) if k in ("breadth_threshold_pct", "min_trades") else v
    for k, v in (new.get("charges") or {}).items():
        if k in s["charges"]:
            v = float(v)
            if v < 0:
                raise ValueError(f"charges.{k} cannot be negative")
            s["charges"][k] = v
    FILE.write_text(json.dumps(s, indent=1))
    return s


def breadth_on():
    return get()["breadth_threshold_pct"] / 100.0
