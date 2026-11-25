"""SQLite store: universe + adjusted daily prices."""
import sqlite3
from contextlib import contextmanager

import pandas as pd

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS universe (
    symbol TEXT PRIMARY KEY, name TEXT, industry TEXT, isin TEXT, updated TEXT
);
CREATE TABLE IF NOT EXISTS prices (
    symbol TEXT NOT NULL, date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (symbol, date)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


@contextmanager
def connect(path=None):
    con = sqlite3.connect(str(path or DB_PATH))
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def save_universe(rows, path=None):
    with connect(path) as con:
        con.execute("DELETE FROM universe")
        con.executemany(
            "INSERT INTO universe(symbol,name,industry,isin,updated) VALUES(?,?,?,?,date('now'))",
            [(r["symbol"], r["name"], r["industry"], r["isin"]) for r in rows])


def load_universe(path=None):
    with connect(path) as con:
        return pd.read_sql("SELECT symbol,name,industry,isin FROM universe ORDER BY symbol", con)


def upsert_prices(symbol, df, path=None):
    """df indexed by date with open/high/low/close/volume columns."""
    if df is None or df.empty:
        return 0
    rows = [(symbol, d.strftime("%Y-%m-%d"), float(r.open), float(r.high), float(r.low),
             float(r.close), float(r.volume)) for d, r in df.iterrows()]
    with connect(path) as con:
        con.executemany("INSERT OR REPLACE INTO prices VALUES(?,?,?,?,?,?,?)", rows)
    return len(rows)


def replace_prices(symbol, df, path=None):
    with connect(path) as con:
        con.execute("DELETE FROM prices WHERE symbol=?", (symbol,))
    return upsert_prices(symbol, df, path)


def load_prices(symbols=None, path=None):
    """-> {symbol: DataFrame(date index, open, high, low, close, volume)}"""
    with connect(path) as con:
        if symbols:
            q = "SELECT * FROM prices WHERE symbol IN (%s) ORDER BY symbol,date" % ",".join("?" * len(symbols))
            df = pd.read_sql(q, con, params=list(symbols))
        else:
            df = pd.read_sql("SELECT * FROM prices ORDER BY symbol,date", con)
    out = {}
    if df.empty:
        return out
    df["date"] = pd.to_datetime(df["date"])
    for sym, g in df.groupby("symbol", sort=False):
        out[sym] = g.drop(columns="symbol").set_index("date")
    return out


def last_dates(path=None):
    with connect(path) as con:
        return dict(con.execute("SELECT symbol, MAX(date) FROM prices GROUP BY symbol").fetchall())


def set_meta(key, value, path=None):
    with connect(path) as con:
        con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, str(value)))


def get_meta(key, path=None):
    with connect(path) as con:
        r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r[0] if r else None
