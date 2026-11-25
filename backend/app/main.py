"""AgentStockAlgo API (port 8100). Recommendations only: no broker orders anywhere in this app.
Run: cd backend && ../.venv/bin/uvicorn app.main:app --port 8100"""
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db, exits, scanner
from .config import BT_SUMMARY_FILE, EXITS_FILE, HOLDINGS_FILE, SCAN_FILE

app = FastAPI(title="AgentStockAlgo", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5190", "http://127.0.0.1:5190"],
                   allow_methods=["*"], allow_headers=["*"])


def _read(path):
    if not path.exists():
        raise HTTPException(404, f"{path.name} not generated yet - run scripts/run_scan.py")
    return json.loads(path.read_text())


@app.get("/api/health")
def health():
    return {"ok": True, "last_ingest": db.get_meta("last_ingest")}


@app.get("/api/scan")
def scan_latest():
    return _read(SCAN_FILE)


@app.post("/api/scan/run")
def scan_run():
    out, feats = scanner.run()
    exits.run(feats)
    return out


@app.get("/api/exits")
def exits_latest():
    return _read(EXITS_FILE)


@app.get("/api/holdings")
def get_holdings():
    return exits.load_holdings()


@app.put("/api/holdings")
def put_holdings(rows: list[dict]):
    for r in rows:
        if not {"symbol", "avg_price"} <= set(r):
            raise HTTPException(422, "each holding needs symbol and avg_price")
    HOLDINGS_FILE.write_text(json.dumps(rows, indent=1))
    return {"saved": len(rows)}


@app.get("/api/backtest")
def backtest_summary():
    return _read(BT_SUMMARY_FILE)
