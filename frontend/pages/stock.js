import { html, useState, useEffect, useRef, useMemo, api, num, pct, cls, go, Badge, Loading, ErrorBox, useUniverse } from "../lib.js";
import { createChart, CrosshairMode } from "https://esm.sh/lightweight-charts@4.2.0";

const C = { up: "#4cc38a", down: "#e5484d", ema: "#8ab4ff", s50: "#a1a1a6", s200: "#5f5f66", grid: "rgba(237,237,237,0.05)", text: "#85858b" };

function Chart({ d, combo }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      autoSize: true, layout: { background: { color: "transparent" }, textColor: C.text, fontFamily: "JetBrains Mono", fontSize: 11 },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: { mode: CrosshairMode.Normal }, rightPriceScale: { borderColor: C.grid }, timeScale: { borderColor: C.grid },
    });
    const candles = chart.addCandlestickSeries({ upColor: C.up, downColor: C.down, borderVisible: false, wickUpColor: "rgba(76,195,138,0.6)", wickDownColor: "rgba(229,72,77,0.6)" });
    candles.setData(d.bars);
    const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol" });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    vol.setData(d.bars.map((b) => ({ time: b.time, value: b.volume, color: "rgba(237,237,237,0.12)" })));
    const line = (data, color, w) => { const s = chart.addLineSeries({ color, lineWidth: w, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }); s.setData(data); };
    line(d.sma200, C.s200, 1); line(d.sma50, C.s50, 1); line(d.ema20, C.ema, 2);
    const first = d.bars.length ? d.bars[0].time : "";
    const marks = [];
    d.trades.filter((t) => `${t.setup}/${t.policy}` === combo).forEach((t) => {
      if (t.entry_date >= first) marks.push({ time: t.entry_date, position: "belowBar", color: C.up, shape: "arrowUp", text: "B" });
      if (t.status === "CLOSED" && t.exit_date >= first)
        marks.push({ time: t.exit_date, position: "aboveBar", color: t.net_pct > 0 ? C.up : C.down, shape: "arrowDown", text: `${t.net_pct > 0 ? "+" : ""}${t.net_pct.toFixed(1)}%` });
    });
    marks.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    candles.setMarkers(marks);
    d.signals.forEach((s) => {
      candles.createPriceLine({ price: s.stop, color: "#ededed", lineStyle: 2, lineWidth: 1, title: "stop" });
      if (s.target) candles.createPriceLine({ price: s.target, color: C.up, lineStyle: 2, lineWidth: 1, title: "target" });
    });
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [d, combo]);
  return html`<div className="chart" ref=${ref}></div>`;
}

export default function Stock({ arg }) {
  const uni = useUniverse();
  const sym = (arg || "").toUpperCase();
  const [q, setQ] = useState(sym);
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [combo, setCombo] = useState("");
  useEffect(() => {
    setQ(sym); setD(null); setErr(null);
    if (!sym) return;
    api(`/stock/${encodeURIComponent(sym)}?days=500`).then((x) => {
      setD(x);
      const combos = [...new Set(x.trades.map((t) => `${t.setup}/${t.policy}`))];
      const pref = x.signals[0] ? `${x.signals[0].setup}/${x.signals[0].exit_policy}` : combos.find((c) => c.endsWith("TRAIL")) || combos[0] || "";
      setCombo(pref);
    }).catch((e) => setErr(e.message));
  }, [sym]);
  const combos = useMemo(() => (d ? [...new Set(d.trades.map((t) => `${t.setup}/${t.policy}`))].sort() : []), [d]);
  const rows = d ? d.trades.filter((t) => `${t.setup}/${t.policy}` === combo).slice().reverse() : [];
  const closed = rows.filter((t) => t.status === "CLOSED");
  const wins = closed.filter((t) => t.net_pct > 0).length;

  return html`
    <div className="head">
      <div><h1>${d ? html`${d.symbol} <span className="sec" style=${{ fontWeight: 400, fontSize: "15px" }}>${d.name}</span>` : "Stock"}</h1>
        <p>${d ? d.industry : "Daily chart, past backtest trades and today's stop"}</p></div>
      <form className="row" onSubmit=${(e) => { e.preventDefault(); if (q) go("/stock/" + q.toUpperCase().trim()); }}>
        <datalist id="syms2">${uni.map((u) => html`<option key=${u.symbol} value=${u.symbol}>${u.name}</option>`)}</datalist>
        <input className="input" list="syms2" placeholder="Symbol" value=${q} onInput=${(e) => setQ(e.target.value.toUpperCase())} />
        <button className="btn primary" type="submit">Open</button>
      </form>
    </div>
    <${ErrorBox} err=${err} />
    ${!sym ? html`<div className="empty">Pick a NIFTY 500 symbol, or open one from Signals or Exits</div>` : null}
    ${sym && !d && !err ? html`<${Loading} what="Loading chart" />` : null}
    ${d ? html`
      <div className="stats">
        <div className="stat"><div className="k">Close</div><div className="v">${num(d.stats.close)}</div><div className="s">ATR ${num(d.stats.atr)}</div></div>
        <div className="stat"><div className="k">From 52-week high</div><div className=${"v " + cls(d.stats.from_52w_high_pct)}>${pct(d.stats.from_52w_high_pct)}</div></div>
        <div className="stat"><div className="k">RS rank (12-month)</div><div className="v">${d.stats.rs_pct ?? "—"}</div><div className="s">percentile in NIFTY 500</div></div>
        <div className="stat"><div className="k">RSI 14</div><div className="v">${d.stats.rsi14 ?? "—"}</div><div className="s">Turnover ₹${num(d.stats.turnover_cr, 1)} cr/day</div></div>
      </div>
      ${d.signals.length ? html`<div className="note">Signal today: ${d.signals.map((s) => html`<span key=${s.setup}><${Badge} v=${s.action} /> ${s.label} — stop ${num(s.stop)}${s.target ? `, target ${num(s.target)}` : ""} </span>`)}</div>` : null}
      <div className="row" style=${{ marginBottom: "8px" }}>
        <span className="sec">Backtest trades</span>
        <select className="input" value=${combo} onChange=${(e) => setCombo(e.target.value)}>
          ${combos.length ? combos.map((c) => html`<option key=${c} value=${c}>${c}</option>`) : html`<option value="">none</option>`}
        </select>
        ${closed.length ? html`<span className="mono muted">${closed.length} closed · win ${Math.round((wins / closed.length) * 100)}% · avg ${pct(closed.reduce((a, t) => a + t.net_pct, 0) / closed.length, 2)}</span>` : null}
      </div>
      <${Chart} d=${d} combo=${combo} />
      <div className="legend">
        <span><i style=${{ background: C.ema }}></i>EMA 20</span><span><i style=${{ background: C.s50 }}></i>SMA 50</span>
        <span><i style=${{ background: C.s200 }}></i>SMA 200</span><span><i style=${{ background: "#ededed" }}></i>Stop today</span><span>B marks a backtest entry, the % marks its exit</span>
      </div>
      ${rows.length ? html`
        <div className="tbl-wrap"><table>
          <thead><tr><th>Signal</th><th>Entry date</th><th className="num">Entry</th><th className="num">Stop</th><th>Exit date</th>
            <th className="num">Exit</th><th>Reason</th><th className="num">Days</th><th className="num">Net</th></tr></thead>
          <tbody>${rows.map((t, i) => html`<tr key=${i}>
            <td>${t.signal_date.slice(0, 10)}</td><td>${t.entry_date.slice(0, 10)}</td><td className="num">${num(t.entry)}</td>
            <td className="num">${num(t.stop0)}</td><td>${t.status === "OPEN" ? html`<span className="tag t-info">Open</span>` : t.exit_date.slice(0, 10)}</td>
            <td className="num">${num(t.exit)}</td><td className="muted">${t.reason}</td><td className="num">${t.days}</td>
            <td className=${"num " + cls(t.net_pct)}>${pct(t.net_pct, 2)}</td></tr>`)}</tbody>
        </table></div>` : null}` : null}`;
}
