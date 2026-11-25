"""Daily after-close job: update prices, scan NIFTY 500, evaluate holdings.
Usage: python scripts/run_scan.py [--no-ingest]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import exits, ingest, scanner, universe  # noqa: E402


def main():
    if "--no-ingest" not in sys.argv:
        rows = universe.refresh()
        c = ingest.run([r["symbol"] for r in rows])
        print(f"Prices updated: incremental={c['incremental']} readjusted={c['readjusted']} full={c['full']}")
    out, feats = scanner.run()
    m = out["market"]
    print(f"As of {out['as_of']}: breadth {m['breadth_pct']}% ({'OK' if m['breadth_ok'] else 'WEAK'}), "
          f"NIFTY 500 above 200 SMA: {m['nifty500_above_200sma']}")
    print(f"{out['counts']['signals']} signals, {out['counts']['consider']} CONSIDER")
    for c in out["signals"][:25]:
        s = c["setup_backtest"]
        print(f"  {c['action']:8s} {c['symbol']:12s} {c['setup']:15s} close {c['close']:>9} stop {c['stop']:>9} "
              f"risk {c['risk_pct']}%  setup PF {s.get('pf')} win {s.get('win_pct')}%  RS {c['rs_pct']}")
    ex = exits.run(feats)
    for h in ex["holdings"]:
        print(f"  HOLDING {h['symbol']:12s} {h['action']:8s} {'; '.join(h['reasons'])}")


if __name__ == "__main__":
    main()
