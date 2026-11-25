"""Adjusted daily OHLCV for NIFTY 500 + benchmarks via yfinance (split/bonus adjusted).

Incremental runs re-download the last ~10 sessions; if the overlap no longer matches what
is stored (a split/bonus re-adjusted history), the symbol's full history is re-fetched.
"""
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from . import db
from .config import BENCHMARK, DOWNLOAD_CHUNK, HISTORY_PERIOD, NIFTY

COLS = ["open", "high", "low", "close", "volume"]


def to_yahoo(sym):
    return sym if sym.startswith("^") else f"{sym}.NS"


def _clean(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=COLS)
    df = df.rename(columns=str.lower)[COLS].dropna(subset=["open", "high", "low", "close"])
    df = df[(df["close"] > 0) & (df["high"] >= df["low"])]
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[~df.index.duplicated(keep="last")]


def download(symbols, period=None, start=None):
    """-> {symbol: cleaned df}. symbols are NSE symbols or ^index tickers."""
    out = {}
    for k in range(0, len(symbols), DOWNLOAD_CHUNK):
        chunk = symbols[k:k + DOWNLOAD_CHUNK]
        tickers = [to_yahoo(s) for s in chunk]
        kw = {"start": start} if start else {"period": period or HISTORY_PERIOD}
        for attempt in range(3):
            try:
                raw = yf.download(tickers, interval="1d", auto_adjust=True, group_by="ticker",
                                  progress=False, threads=True, **kw)
                break
            except Exception:
                if attempt == 2:
                    raw = None
                time.sleep(3 * (attempt + 1))
        for s, t in zip(chunk, tickers):
            try:
                part = raw[t] if raw is not None and len(tickers) > 1 else raw
                out[s] = _clean(part)
            except Exception:
                out[s] = pd.DataFrame(columns=COLS)
        time.sleep(0.5)
    return out


def run(symbols, full=False, log=print):
    """Ingest symbols (+ benchmarks). Returns counts."""
    symbols = list(dict.fromkeys(list(symbols) + [BENCHMARK, NIFTY]))
    have = db.last_dates()
    fresh = [s for s in symbols if full or s not in have]
    incr = [s for s in symbols if s not in fresh]
    counts = {"full": 0, "incremental": 0, "readjusted": 0, "empty": [], "rows": 0}

    if fresh:
        log(f"Full history for {len(fresh)} symbols ({HISTORY_PERIOD})...")
        for s, df in download(fresh, period=HISTORY_PERIOD).items():
            if df.empty:
                counts["empty"].append(s)
                continue
            counts["rows"] += db.replace_prices(s, df)
            counts["full"] += 1

    if incr:
        oldest = min(have[s] for s in incr)
        start = (datetime.strptime(oldest, "%Y-%m-%d") - timedelta(days=15)).strftime("%Y-%m-%d")
        log(f"Incremental update for {len(incr)} symbols from {start}...")
        stored = db.load_prices(incr)
        readjust = []
        for s, df in download(incr, start=start).items():
            if df.empty:
                counts["empty"].append(s)
                continue
            old = stored.get(s)
            if old is not None:
                common = df.index.intersection(old.index)
                if len(common):
                    diff = (df.loc[common, "close"] / old.loc[common, "close"] - 1).abs().max()
                    if diff > 0.01:
                        readjust.append(s)
                        continue
            counts["rows"] += db.upsert_prices(s, df)
            counts["incremental"] += 1
        if readjust:
            log(f"History re-adjusted (split/bonus) for {len(readjust)}: re-fetching full history")
            for s, df in download(readjust, period=HISTORY_PERIOD).items():
                if not df.empty:
                    counts["rows"] += db.replace_prices(s, df)
                    counts["readjusted"] += 1
    db.set_meta("last_ingest", datetime.now().isoformat(timespec="seconds"))
    return counts
