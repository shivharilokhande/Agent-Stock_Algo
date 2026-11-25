"""AgentStockAlgo API + UI on one port (8100). Recommendations only: no broker orders anywhere.
Run: cd backend && ../.venv/bin/uvicorn app.main:app --port 8100   ->  http://localhost:8100"""
import json
import threading

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db, exits, scanner, settings
from .backtest import build_features
from .config import (BENCHMARK, BT_SUMMARY_FILE, BT_TRADES_FILE, EXITS_FILE, HOLDINGS_FILE, NIFTY,
                     ROOT, SCAN_FILE)
from .setups import POLICIES, SETUPS

app = FastAPI(title="AgentStockAlgo", version="0.2.0")
UI = ROOT / "frontend"
_lock = threading.Lock()
_cache = {"feats": None}


def _read(path):
    if not path.exists():
        raise HTTPException(404, f"{path.name} not generated yet - press Run scan")
    return json.loads(path.read_text())


def _feats(refresh=False):
    with _lock:
        if refresh or _cache["feats"] is None:
            uni = set(db.load_universe()["symbol"])
            allp = db.load_prices()
            bench = allp.pop(BENCHMARK, None)
            allp.pop(NIFTY, None)
            _cache["feats"] = build_features({s: d for s, d in allp.items() if s in uni}, bench)
        return _cache["feats"]


def _num(x, n=2):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


@app.get("/api/health")
def health():
    return {"ok": True, "last_ingest": db.get_meta("last_ingest"),
            "scan_generated": _read(SCAN_FILE).get("generated") if SCAN_FILE.exists() else None}


@app.get("/api/scan")
def scan_latest():
    return _read(SCAN_FILE)


@app.post("/api/scan/run")
def scan_run(ingest: bool = False):
    """Optionally refresh prices first (?ingest=true), then scan and evaluate holdings."""
    if ingest:
        from . import ingest as ing, universe
        rows = universe.refresh()
        ing.run([r["symbol"] for r in rows], log=lambda *_: None)
    out, feats = scanner.run()
    with _lock:
        _cache["feats"] = feats
    exits.run(feats)
    return out


@app.get("/api/exits")
def exits_latest():
    if not EXITS_FILE.exists():
        return exits.run(_feats())
    return _read(EXITS_FILE)


@app.get("/api/holdings")
def get_holdings():
    return exits.load_holdings()


@app.put("/api/holdings")
def put_holdings(rows: list[dict]):
    clean = []
    for r in rows:
        if not r.get("symbol") or not r.get("avg_price"):
            raise HTTPException(422, "each holding needs a symbol and avg_price")
        clean.append({"symbol": str(r["symbol"]).upper().strip(), "qty": r.get("qty"),
                      "avg_price": float(r["avg_price"]), "buy_date": r.get("buy_date") or None,
                      "horizon": "long" if r.get("horizon") == "long" else "swing"})
    HOLDINGS_FILE.write_text(json.dumps(clean, indent=1))
    return exits.run(_feats())


@app.get("/api/universe")
def universe_list():
    return db.load_universe().to_dict("records")


@app.get("/api/stock/{symbol}")
def stock(symbol: str, days: int = 400):
    sym = symbol.upper()
    f = _feats().get(sym)
    if f is None:
        raise HTTPException(404, f"{sym} is not in the NIFTY 500 data")
    t = f.iloc[-days:]
    ts = [d.strftime("%Y-%m-%d") for d in t.index]

    def line(col):
        return [{"time": d, "value": _num(v)} for d, v in zip(ts, t[col].values) if np.isfinite(v)]
    bars = [{"time": d, "open": _num(r.open), "high": _num(r.high), "low": _num(r.low),
             "close": _num(r.close), "volume": float(r.volume)} for d, r in zip(ts, t.itertuples())]
    trades = []
    if BT_TRADES_FILE.exists():
        bt = pd.read_csv(BT_TRADES_FILE)
        bt = bt[bt["symbol"] == sym]
        trades = json.loads(bt[["setup", "policy", "signal_date", "entry_date", "entry", "stop0", "exit_date",
                                "exit", "reason", "status", "net_pct", "days"]].round(2).to_json(orient="records"))
    signals = []
    if SCAN_FILE.exists():
        signals = [c for c in json.loads(SCAN_FILE.read_text())["signals"] if c["symbol"] == sym]
    last = f.iloc[-1]
    uni = db.load_universe().set_index("symbol")
    return {"symbol": sym, "name": uni.at[sym, "name"] if sym in uni.index else sym,
            "industry": uni.at[sym, "industry"] if sym in uni.index else "",
            "bars": bars, "ema20": line("ema20"), "sma50": line("sma50"), "sma200": line("sma200"),
            "trades": trades, "signals": signals,
            "stats": {"close": _num(last["close"]), "atr": _num(last["atr14"]), "rsi14": _num(last["rsi14"], 1),
                      "rs_pct": _num(last["rs_pct"] * 100, 0) if pd.notna(last["rs_pct"]) else None,
                      "from_52w_high_pct": _num((last["close"] / last["hi252"] - 1) * 100, 1),
                      "turnover_cr": _num(last["turnover_cr"], 1)}}


@app.get("/api/backtest")
def backtest_summary():
    doc = _read(BT_SUMMARY_FILE)
    doc["setups"] = {s.key: {"label": s.label, "horizon": s.horizon, "rule": (s.signal.__doc__ or "").strip(),
                             "note": s.note} for s in SETUPS}
    doc["policies"] = {k: v["desc"] for k, v in POLICIES.items()}
    return doc


@app.post("/api/backtest/run")
def backtest_run():
    from .study import run_study
    meta = run_study(log=lambda *_: None)
    out, feats = scanner.run()                   # scan cards use the fresh stats
    with _lock:
        _cache["feats"] = feats
    exits.run(feats)
    return meta


@app.get("/api/settings")
def get_settings():
    return settings.get()


@app.put("/api/settings")
def put_settings(body: dict):
    try:
        return settings.save(body)
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))


# ---- UI (no build step: static ES modules served from ../frontend) ----
if UI.exists():
    app.mount("/static", StaticFiles(directory=UI), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        return FileResponse(UI / "index.html")
