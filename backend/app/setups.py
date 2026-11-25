"""Trade setups on DAILY bars. A signal at bar t is decided on t's close; entry is t+1's open.

Each setup: signal(f) -> bool Series, stop(f) -> initial stop price Series, horizon, and the
exit policies it is tested with. AgentAlgo analogues are noted for reference only (no code shared).
"""
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Setup:
    key: str
    label: str
    horizon: str                     # swing | long
    signal: callable
    stop: callable
    policies: list = field(default_factory=list)
    note: str = ""


def _liquid(f):
    return (f["turnover_cr"] >= 5) & (f["close"] >= 50)


def pullback_ema20(f):
    """TREND_PB analogue: strong uptrend, recently stretched >=6% above EMA20, today dips to
    EMA20 (low within 1%) and closes back above it as a green candle."""
    up = (f["close"] > f["sma50"]) & (f["sma50"] > f["sma200"]) & f["sma200_up"]
    stretched = f["stretch10"].shift(1) >= 0.06
    touch = f["low"] <= f["ema20"] * 1.01
    hold = (f["close"] > f["ema20"]) & (f["close"] > f["open"])
    return up & stretched & touch & hold & _liquid(f)


def breakout_55(f):
    """55-day high breakout on >=1.5x volume, strong close, above SMA200, not overextended."""
    return ((f["close"] > f["hh55_prev"]) & (f["volume"] >= 1.5 * f["vol20"]) &
            (f["range_pos"] >= 0.7) & (f["close"] > f["sma200"]) & (f["ext20"] <= 0.10) & _liquid(f))


def reclaim_sma50(f):
    """VWAP_RECLAIM analogue on daily: closes back above SMA50 inside a rising long-term trend."""
    return ((f["close"].shift(1) < f["sma50"].shift(1)) & (f["close"] > f["sma50"]) &
            (f["close"] > f["sma200"]) & f["sma200_up"] & (f["volume"] >= f["vol20"]) & _liquid(f))


def rsi2_dip(f):
    """Short-term oversold (RSI2 < 10) inside an uptrend; exit on close above SMA5."""
    return (f["rsi2"] < 10) & (f["close"] > f["sma200"]) & (f["sma50"] > f["sma200"]) & _liquid(f)


def trend_template(f):
    """Long-term trend template: 50>150>200 stack, 200 rising, >=30% off 52w low, within 25%
    of 52w high, 12-month relative strength in the top 30% of NIFTY 500. Fires on the first
    day the full template is true after 20+ days of not being true."""
    cond = ((f["close"] > f["sma50"]) & (f["sma50"] > f["sma150"]) & (f["sma150"] > f["sma200"]) &
            f["sma200_up"] & (f["close"] >= 1.3 * f["lo252"]) & (f["close"] >= 0.75 * f["hi252"]) &
            (f["rs_pct"] >= 0.70) & _liquid(f)).fillna(False)
    prior = cond.shift(1).fillna(False).astype(int).rolling(20, min_periods=1).sum()
    return cond & (prior == 0)


SETUPS = [
    Setup("PULLBACK_EMA20", "Pullback to 20 EMA", "swing", pullback_ema20,
          lambda f: f["low"] - 0.5 * f["atr14"], ["R2", "TRAIL"], "TREND_PB analogue"),
    Setup("BREAKOUT_55", "55-day breakout on volume", "swing", breakout_55,
          lambda f: f["close"] - 2.0 * f["atr14"], ["R2", "TRAIL"]),
    Setup("RECLAIM_SMA50", "Reclaim of 50 SMA", "swing", reclaim_sma50,
          lambda f: pd.concat([f["low10"], f["close"] - 1.5 * f["atr14"]], axis=1).min(axis=1),
          ["R2", "TRAIL"], "VWAP_RECLAIM analogue"),
    Setup("RSI2_DIP", "RSI(2) dip in uptrend", "swing", rsi2_dip,
          lambda f: f["close"] - 2.5 * f["atr14"], ["MA5"]),
    Setup("TREND_TEMPLATE", "Long-term trend template", "long", trend_template,
          lambda f: f["close"] * 0.85, ["LONG"]),
]
SETUP_BY_KEY = {s.key: s for s in SETUPS}

# Market regime used by the scanner: share of NIFTY 500 stocks above their own 50-day SMA.
# Chosen from the 25-Nov-2026 study (best separator of all regime tests, every setup) - in-sample.
BREADTH_ON = 0.60

# Exit policies
POLICIES = {
    "R2": {"target_r": 2.0, "max_days": 20, "desc": "stop / 2R target / 20-day time exit"},
    "TRAIL": {"trail_atr": 3.0, "max_days": 60, "desc": "stop, then 3xATR chandelier trail off highest close / 60 days"},
    "MA5": {"max_days": 10, "desc": "exit next open after a close above SMA5 / stop / 10 days"},
    "LONG": {"max_days": 750, "desc": "15% stop, exit next open after a close below SMA150"},
}
