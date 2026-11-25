"""NIFTY 500 constituents from niftyindices.com (cached in SQLite)."""
import csv
import io

import httpx

from . import db
from .config import DATA, UNIVERSE_URL

CACHE = DATA / "nifty500.csv"


def fetch_nifty500():
    try:
        r = httpx.get(UNIVERSE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20, follow_redirects=True)
        r.raise_for_status()
        text = r.text
        CACHE.write_text(text)
    except Exception:
        if not CACHE.exists():
            raise
        text = CACHE.read_text()
    return parse(text)


def parse(text):
    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        sym = (rec.get("Symbol") or "").strip()
        if not sym or (rec.get("Series") or "EQ").strip() != "EQ":
            continue
        rows.append({"symbol": sym, "name": (rec.get("Company Name") or "").strip(),
                     "industry": (rec.get("Industry") or "").strip(),
                     "isin": (rec.get("ISIN Code") or "").strip()})
    return rows


def refresh():
    rows = fetch_nifty500()
    db.save_universe(rows)
    return rows
