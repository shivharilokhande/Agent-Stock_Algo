import { html, useState, useMemo, api, useApi, num, pct, pfCls, Badge, Loading, ErrorBox, useToast } from "../lib.js";

function Market({ scan }) {
  const m = scan.market;
  const ok = m.breadth_ok;
  const color = ok ? "var(--green)" : m.breadth_pct >= m.breadth_threshold_pct - 10 ? "var(--amber)" : "var(--red)";
  return html`
    <div className="tiles">
      <div className="panel tile">
        <div className="k">Market breadth (above own 50-day SMA)</div>
        <div className="v" style=${{ color }}>${num(m.breadth_pct, 1)}%</div>
        <div className="gauge"><i style=${{ width: Math.min(100, m.breadth_pct) + "%", background: color }}></i>
          <b style=${{ left: m.breadth_threshold_pct + "%" }} title="gate"></b></div>
        <div className="s">Gate ${m.breadth_threshold_pct}% · ${ok ? "healthy" : "weak"}</div>
      </div>
      <div className="panel tile">
        <div className="k">NIFTY 500 vs 200-day SMA</div>
        <div className="v" style=${{ color: m.nifty500_above_200sma ? "var(--green)" : "var(--red)" }}>${m.nifty500_above_200sma ? "Above" : "Below"}</div>
        <div className="s">Context only — breadth is the gate</div>
      </div>
      <div className="panel tile">
        <div className="k">Signals today</div>
        <div className="v">${scan.counts.signals}</div>
        <div className="s">${scan.counts.consider} CONSIDER · ${scan.counts.signals - scan.counts.consider} WATCH</div>
      </div>
      <div className="panel tile">
        <div className="k">As of</div>
        <div className="v" style=${{ fontSize: "18px" }}>${scan.as_of}</div>
        <div className="s">Scanned ${scan.counts.stocks} stocks · ${(scan.generated || "").replace("T", " ")}</div>
      </div>
    </div>
    <div className=${"note" + (ok ? " info" : "")}>${m.note}</div>`;
}

function Card({ c }) {
  const s = c.setup_backtest || {};
  const h = c.stock_history || {};
  return html`
    <div className=${"card" + (c.action === "CONSIDER" ? " consider" : "")}>
      <div className="top">
        <div>
          <a className="sym" href=${"#/stock/" + encodeURIComponent(c.symbol)}>${c.symbol}</a>
          <div className="nm" title=${c.name}>${c.name} · ${c.industry}</div>
        </div>
        <div style=${{ textAlign: "right" }}>
          <${Badge} v=${c.action} />
          <div className="faint" style=${{ fontSize: "11px", marginTop: "4px" }}>${c.horizon}</div>
        </div>
      </div>
      <div><span className="badge b-blue">${c.label}</span> <span className="faint" style=${{ fontSize: "12px" }}>exit ${c.exit_policy}</span></div>
      <div className="kv">
        <div><span>Close</span><b>${num(c.close)}</b></div>
        <div><span>Stop</span><b className="down">${num(c.stop)}</b></div>
        <div><span>${c.target ? "Target" : "Risk"}</span><b className=${c.target ? "up" : ""}>${c.target ? num(c.target) : pct(c.risk_pct, 1, false)}</b></div>
        <div><span>RS rank</span><b>${c.rs_pct ?? "—"}</b></div>
      </div>
      <div className="bt">
        <span>Setup backtest: PF <b className=${pfCls(s.pf)}>${s.pf ?? "—"}</b></span>
        <span>win <b>${s.win_pct ?? "—"}%</b></span>
        <span>avg <b className=${s.avg_net_pct > 0 ? "up" : "down"}>${pct(s.avg_net_pct, 2)}</b></span>
        <span><b>${s.trades ?? 0}</b> trades</span>
      </div>
      <div className="faint" style=${{ fontSize: "12px" }}>
        On ${c.symbol}: ${h.trades ? html`${h.trades} past trades, win ${h.win_pct}%, avg ${pct(h.avg_net_pct, 2)}` : "no past trades of this setup"}
        · risk ${pct(c.risk_pct, 1, false)} · ${pct(c.ext_from_ema20_pct, 1)} vs EMA20
      </div>
      <div className="faint" style=${{ fontSize: "11px" }}>${c.exit_rule}. Buy at next open; skip if it opens below the stop.</div>
    </div>`;
}

export default function Today() {
  const { data, err, loading, setData, reload } = useApi("/scan");
  const [busy, setBusy] = useState(null);
  const [action, setAction] = useState("ALL");
  const [horizon, setHorizon] = useState("all");
  const [setup, setSetup] = useState("all");
  const [q, setQ] = useState("");
  const [toast, show] = useToast();

  const run = async (ingest) => {
    setBusy(ingest ? "Updating prices and scanning…" : "Scanning…");
    try {
      const d = await api("/scan/run" + (ingest ? "?ingest=true" : ""), { method: "POST" });
      setData(d);
      show(`Scan done: ${d.counts.signals} signals, ${d.counts.consider} CONSIDER`);
    } catch (e) { show("Scan failed: " + e.message); }
    setBusy(null);
  };

  const setups = useMemo(() => [...new Set((data?.signals || []).map((c) => c.setup))], [data]);
  const list = useMemo(() => (data?.signals || []).filter((c) =>
    (action === "ALL" || c.action === action) && (horizon === "all" || c.horizon === horizon) &&
    (setup === "all" || c.setup === setup) &&
    (!q || c.symbol.includes(q.toUpperCase()) || (c.name || "").toUpperCase().includes(q.toUpperCase()))), [data, action, horizon, setup, q]);

  return html`
    <div className="head">
      <div><h1>Today's opportunities</h1><p>Signals from the latest daily close. Recommendations only — you decide and place every trade.</p></div>
      <div className="row">
        <button className="btn" disabled=${!!busy} onClick=${() => run(false)}>Re-scan</button>
        <button className="btn primary" disabled=${!!busy} onClick=${() => run(true)}>${busy || "Update prices + scan"}</button>
      </div>
    </div>
    ${err && err.includes("not generated") ? html`<div className="empty">No scan yet. Press <b>Update prices + scan</b>.</div>` : html`<${ErrorBox} err=${err} />`}
    ${loading && !data ? html`<${Loading} />` : null}
    ${data ? html`
      <${Market} scan=${data} />
      <div className="row" style=${{ marginBottom: "14px" }}>
        <div className="seg">${["ALL", "CONSIDER", "WATCH"].map((a) => html`<button key=${a} className=${action === a ? "on" : ""} onClick=${() => setAction(a)}>${a === "ALL" ? "All" : a}</button>`)}</div>
        <div className="seg">${["all", "swing", "long"].map((a) => html`<button key=${a} className=${horizon === a ? "on" : ""} onClick=${() => setHorizon(a)}>${a[0].toUpperCase() + a.slice(1)}</button>`)}</div>
        <select className="input" value=${setup} onChange=${(e) => setSetup(e.target.value)}>
          <option value="all">All setups</option>
          ${setups.map((s) => html`<option key=${s} value=${s}>${s}</option>`)}
        </select>
        <input className="input" placeholder="Search symbol or name" value=${q} onInput=${(e) => setQ(e.target.value)} />
        <span className="faint">${list.length} shown</span>
      </div>
      ${list.length ? html`<div className="cards">${list.map((c) => html`<${Card} key=${c.symbol + c.setup} c=${c} />`)}</div>`
        : html`<div className="empty">No signals match these filters.</div>`}` : null}
    ${toast}`;
}
