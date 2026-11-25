import { html, useState, useMemo, api, useApi, num, pct, day, Badge, Track, PfBar, Loading, ErrorBox, useToast } from "../lib.js";

function Gate({ m }) {
  const ok = m.breadth_ok;
  return html`
    <div className="gate">
      <div>
        <div className="lbl">Market breadth</div>
        <div className="fig">${num(m.breadth_pct, 1)}%</div>
        <div className="verdict"><span className="dot" style=${{ background: ok ? "var(--pos)" : "var(--warn)" }}></span>
          ${ok ? "Above the gate" : `${num(m.breadth_threshold_pct - m.breadth_pct, 1)} pts below the gate`}</div>
      </div>
      <div>
        <${Track} value=${m.breadth_pct} min=${m.breadth_threshold_pct} max=${100} />
        <div className="scale"><span>0%</span><span>gate ${m.breadth_threshold_pct}%</span><span>100%</span></div>
        <div className="msg">Share of NIFTY 500 stocks closing above their own 50-day average. ${m.note}.
          NIFTY 500 is ${m.nifty500_above_200sma ? "above" : "below"} its 200-day average.</div>
      </div>
    </div>`;
}

function Group({ g, minPf }) {
  const s = g.stats || {};
  return html`
    <div className="group">
      <div className="group-head">
        <div>
          <h2>${g.label} <span className="muted" style=${{ fontWeight: 400 }}>· ${g.horizon} · ${g.rows.length}</span></h2>
          <div className="rule">${g.rule}</div>
        </div>
        <div className="meta">
          <span>Backtest PF <${PfBar} pf=${s.pf} min=${minPf} /></span>
          <span>win ${s.win_pct ?? "—"}%</span>
          <span>avg ${pct(s.avg_net_pct, 2)}</span>
          <span className="mono">${(s.trades ?? 0).toLocaleString("en-IN")} trades</span>
        </div>
      </div>
      <div className="tbl-wrap"><table>
        <thead><tr><th>Stock</th><th></th><th className="num">Close</th><th className="num">Stop</th>${g.hasTarget ? html`<th className="num">Target</th>` : null}
          <th className="num">RS rank</th><th className="num">vs EMA20</th><th className="num">Turnover</th><th>On this stock before</th></tr></thead>
        <tbody>${g.rows.map((c) => {
          const h = c.stock_history || {};
          return html`<tr key=${c.symbol} className=${c.action === "CONSIDER" ? "consider" : ""}>
            <td><a className="sym" href=${"#/stock/" + encodeURIComponent(c.symbol)}>${c.symbol}</a><span className="name" title=${c.name}>${c.name}</span></td>
            <td><${Badge} v=${c.action} /></td>
            <td className="num">${num(c.close)}</td>
            <td className="num">${num(c.stop)}<div className="muted mono">${pct(-c.risk_pct, 1)}</div></td>
            ${g.hasTarget ? html`<td className="num">${num(c.target)}</td>` : null}
            <td className="num">${c.rs_pct ?? "—"}</td>
            <td className="num">${pct(c.ext_from_ema20_pct, 1)}</td>
            <td className="num mono">₹${num(c.turnover_cr, 0)} cr</td>
            <td className="sec">${h.trades ? html`${h.trades} trades · win ${h.win_pct}% · avg <span className=${h.avg_net_pct >= 0 ? "up" : "down"}>${pct(h.avg_net_pct, 2)}</span>` : html`<span className="muted">none</span>`}</td>
          </tr>`;
        })}</tbody>
      </table></div>
    </div>`;
}

export default function Today() {
  const { data, err, loading, setData } = useApi("/scan");
  const [busy, setBusy] = useState(null);
  const [action, setAction] = useState("ALL");
  const [horizon, setHorizon] = useState("all");
  const [q, setQ] = useState("");
  const [toast, show] = useToast();

  const run = async (ingest) => {
    setBusy(ingest ? "Updating prices" : "Scanning");
    try {
      const d = await api("/scan/run" + (ingest ? "?ingest=true" : ""), { method: "POST" });
      setData(d);
      show(`${d.counts.signals} signals, ${d.counts.consider} to consider`);
    } catch (e) { show("Scan failed: " + e.message); }
    setBusy(null);
  };

  const groups = useMemo(() => {
    const out = new Map();
    for (const c of data?.signals || []) {
      if (action !== "ALL" && c.action !== action) continue;
      if (horizon !== "all" && c.horizon !== horizon) continue;
      if (q && !c.symbol.includes(q.toUpperCase()) && !(c.name || "").toUpperCase().includes(q.toUpperCase())) continue;
      const k = c.setup + "/" + c.exit_policy;
      if (!out.has(k)) out.set(k, { key: k, label: c.label, horizon: c.horizon, rule: c.exit_rule, stats: c.setup_backtest, hasTarget: !!c.target, rows: [] });
      out.get(k).rows.push(c);
    }
    return [...out.values()].sort((a, b) => (b.stats?.pf || 0) - (a.stats?.pf || 0));
  }, [data, action, horizon, q]);
  const shown = groups.reduce((n, g) => n + g.rows.length, 0);

  return html`
    <div className="head">
      <div><h1>${data ? `Signals from the ${day(data.as_of)} close` : "Signals"}</h1>
        <p>${data ? `${data.counts.signals} signals across ${data.counts.stocks} NIFTY 500 stocks · ${data.counts.consider} to consider` : "NIFTY 500, daily close"}</p></div>
      <div className="row">
        <button className="btn" disabled=${!!busy} onClick=${() => run(false)}>Re-scan</button>
        <button className="btn primary" disabled=${!!busy} onClick=${() => run(true)}>${busy ? busy + "…" : "Update prices and scan"}</button>
      </div>
    </div>
    ${err && err.includes("not generated") ? html`<div className="empty">No scan yet. Use Update prices and scan</div>` : html`<${ErrorBox} err=${err} />`}
    ${loading && !data ? html`<${Loading} />` : null}
    ${data ? html`
      <${Gate} m=${data.market} />
      <div className="row" style=${{ marginBottom: "16px" }}>
        <div className="seg">${[["ALL", "All"], ["CONSIDER", "Consider"], ["WATCH", "Watch"]].map(([a, l]) => html`<button key=${a} className=${action === a ? "on" : ""} onClick=${() => setAction(a)}>${l}</button>`)}</div>
        <div className="seg">${[["all", "All"], ["swing", "Swing"], ["long", "Long-term"]].map(([a, l]) => html`<button key=${a} className=${horizon === a ? "on" : ""} onClick=${() => setHorizon(a)}>${l}</button>`)}</div>
        <input className="input" placeholder="Search" value=${q} onInput=${(e) => setQ(e.target.value)} />
        <span className="mono muted">${shown} shown</span>
      </div>
      ${groups.length ? groups.map((g) => html`<${Group} key=${g.key} g=${g} minPf=${data.market.min_pf ?? 1.2} />`)
        : html`<div className="empty">No signals match these filters</div>`}
      <p className="muted" style=${{ fontSize: "12px" }}>Buy at the next open and skip it if the open is below the stop. Consider needs breadth above the gate and the setup's backtest PF at or above ${data.market.min_pf ?? 1.2}.</p>` : null}
    ${toast}`;
}
