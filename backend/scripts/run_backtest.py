"""Backtest every setup x exit policy on the stored NIFTY 500 history and write the study.

Usage: python scripts/run_backtest.py
Writes: data/backtest_trades.csv, data/backtest_summary.json, docs/studies/YYYY-MM-DD-backtest.md
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import backtest, db  # noqa: E402
from app.config import BENCHMARK, BT_SUMMARY_FILE, BT_TRADES_FILE, NIFTY, STUDIES  # noqa: E402
from app.setups import BREADTH_ON, POLICIES, SETUP_BY_KEY  # noqa: E402


def fmt(s):
    if not s or not s.get("trades"):
        return "| 0 | | | | | | |"
    pf = s["pf"] if s["pf"] is not None else "inf"
    return (f"| {s['trades']} | {s['win_pct']}% | {s['avg_net_pct']}% | {pf} | {s['avg_net_r']} | "
            f"{s['avg_days']} | {s['pct_per_day']}% |")


def main():
    t0 = time.time()
    uni = set(db.load_universe()["symbol"])
    allp = db.load_prices()
    bench = allp.pop(BENCHMARK, None)
    allp.pop(NIFTY, None)
    prices = {s: d for s, d in allp.items() if s in uni}
    print(f"Backtesting {len(prices)} stocks, {min(d.index[0] for d in prices.values()).date()} .. "
          f"{max(d.index[-1] for d in prices.values()).date()}")
    trades = backtest.run(prices, bench, log=print)
    trades.drop(columns=["exit_idx"]).to_csv(BT_TRADES_FILE, index=False)
    summary = backtest.summarize(trades)
    meta = {"run_date": date.today().isoformat(), "stocks": len(prices),
            "start": str(min(d.index[0] for d in prices.values()).date()),
            "end": str(max(d.index[-1] for d in prices.values()).date()),
            "trades": int(len(trades)), "seconds": round(time.time() - t0)}
    BT_SUMMARY_FILE.write_text(json.dumps({"meta": meta, "results": summary}, indent=1, default=str))

    hdr = "| Trades | Win | Avg net | PF | Avg net R | Avg days | Net %/day |\n|---|---|---|---|---|---|---|"
    L = [f"# Backtest study — {meta['run_date']}", "",
         f"NIFTY 500 (current constituents, {meta['stocks']} stocks), adjusted daily data "
         f"{meta['start']} → {meta['end']}. First ~1 year is indicator warm-up (SMA200 / 52-week).",
         "Entry next open after the signal close, slippage 0.10% each side, delivery charges on "
         "₹1 lakh per trade (STT, exchange, SEBI, stamp, GST, DP). Net figures are after all of it.", "",
         "**Read with care:** current-constituent universe = survivorship bias (stocks that fell out "
         "of NIFTY 500 are missing), so results are flattered. Trades overlap in time; this is a "
         "per-trade study, not a portfolio equity curve.", "",
         "## Overview (all closed trades)", "",
         "| Setup | Exit | " + hdr.split("\n")[0][2:], "|---|---|" + hdr.split("\n")[1][1:]]
    for r in sorted(summary, key=lambda x: (x["horizon"], x["setup"], x["policy"])):
        L.append(f"| {r['setup']} | {r['policy']} " + fmt(r["all"]))
    L += ["", "## Regime split (NIFTY 500 above / below its 200-day SMA on the signal day)", "",
          "| Setup | Exit | Regime | " + hdr.split("\n")[0][2:], "|---|---|---|" + hdr.split("\n")[1][1:]]
    for r in sorted(summary, key=lambda x: (x["horizon"], x["setup"], x["policy"])):
        L.append(f"| {r['setup']} | {r['policy']} | ON " + fmt(r["regime_on"]))
        L.append(f"| {r['setup']} | {r['policy']} | OFF " + fmt(r["regime_off"]))
    L += ["", f"## Breadth regime (≥{int(BREADTH_ON * 100)}% of NIFTY 500 above their own 50-day SMA) — used by the scanner", "",
          "Chosen after comparing 5 regime definitions; it separated good and bad periods best for "
          "every setup. In-sample choice, so treat as a hypothesis to forward-test.", "",
          "| Setup | Exit | Breadth | " + hdr.split("\n")[0][2:], "|---|---|---|" + hdr.split("\n")[1][1:]]
    for r in sorted(summary, key=lambda x: (x["horizon"], x["setup"], x["policy"])):
        L.append(f"| {r['setup']} | {r['policy']} | ON all " + fmt(r["breadth_on"]))
        L.append(f"| {r['setup']} | {r['policy']} | OFF all " + fmt(r["breadth_off"]))
        L.append(f"| {r['setup']} | {r['policy']} | ON last 40% " + fmt(r["breadth_on_last_40"]))
        L.append(f"| {r['setup']} | {r['policy']} | OFF last 40% " + fmt(r["breadth_off_last_40"]))
    op = trades[trades["status"] == "OPEN"]
    L += ["", "## Still-open trades (marked to today's close, net of exit charges)", "",
          "Recent closed trades are biased toward losers because recent winners are still open — "
          "most visible for the long-term setup.", "",
          "| Setup | Exit | Open | Avg net | In profit |", "|---|---|---|---|---|"]
    for (s, p), g in op.groupby(["setup", "policy"]):
        L.append(f"| {s} | {p} | {len(g)} | {g['net_pct'].mean():.2f}% | {(g['net_pnl'] > 0).mean() * 100:.0f}% |")
    L += ["", "## Stability (first 60% of signals vs last 40%)", "",
          "| Setup | Exit | Part | " + hdr.split("\n")[0][2:], "|---|---|---|" + hdr.split("\n")[1][1:]]
    for r in sorted(summary, key=lambda x: (x["horizon"], x["setup"], x["policy"])):
        L.append(f"| {r['setup']} | {r['policy']} | first 60% " + fmt(r["first_60"]))
        L.append(f"| {r['setup']} | {r['policy']} | last 40% " + fmt(r["last_40"]))
    L += ["", "## By year (signal year)", ""]
    for r in sorted(summary, key=lambda x: (x["horizon"], x["setup"], x["policy"])):
        L += [f"**{r['setup']} / {r['policy']}** — exits: " +
              ", ".join(f"{k} {v}" for k, v in r["exits"].items()) + f"; open now: {r['open_now']}", "",
              "| Year | " + hdr.split("\n")[0][2:], "|---|" + hdr.split("\n")[1][1:]]
        for y, s in r["by_year"].items():
            L.append(f"| {y} " + fmt(s))
        L.append("")
    L += ["## Definitions", ""]
    for k, st in SETUP_BY_KEY.items():
        L.append(f"- **{k}** ({st.horizon}): {st.signal.__doc__.strip()}")
    for k, p in POLICIES.items():
        L.append(f"- Exit **{k}**: {p['desc']}")
    out = STUDIES / f"{meta['run_date']}-backtest.md"
    out.write_text("\n".join(L) + "\n")
    print(f"{meta['trades']} trades in {meta['seconds']}s -> {out}")


if __name__ == "__main__":
    main()
