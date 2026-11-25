"""Indicators on daily bars. Every value at bar t uses data up to and including t only."""
import numpy as np
import pandas as pd


def sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def wilder(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def atr(high, low, close, n=14):
    pc = close.shift(1)
    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    return wilder(tr, n)


def rsi(close, n=14):
    d = close.diff()
    au = wilder(d.clip(lower=0), n)
    ad = wilder((-d).clip(lower=0), n)
    r = 100 - 100 / (1 + au / ad.replace(0, np.nan))
    return r.where(~((ad == 0) & au.notna()), 100.0)


def features(df, bench_close=None, rs_pct=None, breadth=None):
    """Adds every column the setups and exits need. df: open/high/low/close/volume."""
    f = df.copy()
    c, h, l, o, v = f["close"], f["high"], f["low"], f["open"], f["volume"]
    f["ema20"] = ema(c, 20)
    f["sma5"] = sma(c, 5)
    f["sma50"] = sma(c, 50)
    f["sma150"] = sma(c, 150)
    f["sma200"] = sma(c, 200)
    f["sma200_up"] = f["sma200"] > f["sma200"].shift(20)
    f["atr14"] = atr(h, l, c, 14)
    f["rsi2"] = rsi(c, 2)
    f["rsi14"] = rsi(c, 14)
    f["hh55_prev"] = h.rolling(55, min_periods=55).max().shift(1)
    f["vol20"] = sma(v, 20).shift(1)
    f["low10"] = l.rolling(10, min_periods=10).min()
    f["hi252"] = h.rolling(252, min_periods=200).max()
    f["lo252"] = l.rolling(252, min_periods=200).min()
    f["ext20"] = c / f["ema20"] - 1
    # largest stretch above EMA20 in the last 10 bars, each bar vs its own EMA20 (one-sided)
    f["stretch10"] = (h / f["ema20"] - 1).rolling(10, min_periods=10).max()
    rng = (h - l).replace(0, np.nan)
    f["range_pos"] = ((c - l) / rng).fillna(0.5)
    f["turnover_cr"] = (c * v / 1e7).rolling(20, min_periods=20).mean()
    if bench_close is not None and len(bench_close):
        b = bench_close.reindex(f.index).ffill()
        f["regime"] = (b > sma(bench_close, 200).reindex(f.index).ffill()).fillna(False)
    else:
        f["regime"] = True
    f["rs_pct"] = rs_pct.reindex(f.index) if rs_pct is not None else np.nan
    f["breadth"] = breadth.reindex(f.index).ffill() if breadth is not None else np.nan
    return f


def market_breadth(closes: dict, n=50):
    """Share (0-1) of stocks closing above their own n-day SMA, per date."""
    panel = pd.DataFrame({s: d["close"] for s, d in closes.items()}).sort_index().ffill(limit=5)
    above = panel > panel.rolling(n, min_periods=n).mean()
    return above.sum(axis=1) / panel.rolling(n, min_periods=n).mean().notna().sum(axis=1).replace(0, np.nan)


def rs_percentile(closes: dict, lookback=252):
    """Cross-sectional percentile (0-1) of each stock's `lookback`-day return, per date."""
    panel = pd.DataFrame({s: d["close"] for s, d in closes.items()}).sort_index().ffill(limit=5)
    ret = panel / panel.shift(lookback) - 1
    return ret.rank(axis=1, pct=True)
