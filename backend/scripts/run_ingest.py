"""Refresh NIFTY 500 universe and adjusted daily prices.  Usage: python -m scripts.run_ingest [--full]"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import ingest, universe  # noqa: E402


def main():
    full = "--full" in sys.argv
    t0 = time.time()
    rows = universe.refresh()
    print(f"Universe: {len(rows)} NIFTY 500 stocks")
    c = ingest.run([r["symbol"] for r in rows], full=full)
    print(f"Done in {time.time() - t0:.0f}s: full={c['full']} incremental={c['incremental']} "
          f"readjusted={c['readjusted']} rows={c['rows']} empty={len(c['empty'])}")
    if c["empty"]:
        print("No data for:", ", ".join(c["empty"][:40]))


if __name__ == "__main__":
    main()
