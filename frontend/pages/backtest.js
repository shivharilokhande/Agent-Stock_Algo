import { html, useState, api, useApi, pct, pfCls, Loading, ErrorBox, useToast } from "../lib.js";

const VIEWS = [
  ["all", "All trades"], ["breadth_on", "Breadth ON"], ["breadth_off", "Breadth OFF"],
  ["breadth_on_last_40", "Breadth ON · recent 40%"], ["breadth_off_last_40", "Breadth OFF · recent 40%"],
  ["first_60", "First 60%"], ["last_40", "Recent 40%"], ["regime_on", "NIFTY500 > 200 SMA"], ["regime_off", "NIFTY500 < 200 SMA"],
];

function Cells({ s }) {
  if (!s || !s.trades) return html`<td className="num faint" colSpan="7">no trades</td>`;
  return html`
    <td className="num">${s.trades}</td>
    <td className="num">${s.win_pct}%</td>
    <td className=${"num " + (s.avg_net_pct > 0 ? "up" : "down")}>${pct(s.avg_net_pct, 2)}</td>
    <td className=${"num " + pfCls(s.pf)}><b>${s.pf ?? "∞"}</b></td>
    <td className="num">${s.avg_net_r}</td>
    <td className="num">${s.avg_days}</td>
    <td className="num">₹${s.avg_charges}</td>`;
}

export default function Backtest() {
  const { data, err, loading, reload } = useApi("/backtest");
  const [view, setView] = useState("breadth_on");
  const [busy, setBusy] = useState(false);
  const [toast, show] = useToast();
  const rerun = async () => {
    setBusy(true);
    try { const m = await api("/backtest/run", { method: "POST" }); show(`Backtest done: ${m.trades} trades in ${m.seconds}s`); reload(); }
    catch (e) { show("Backtest failed: " + e.message); }
    setBusy(false);
  };
  const res = (data?.results || []).slice().sort((a, b) => (a.horizon + a.setup + a.policy).localeCompare(b.horizon + b.setup + b.policy));
  return html`
    <div className="head">
      <div><h1>Backtest</h1><p>${data ? `${data.meta.stocks} NIFTY 500 stocks · ${data.meta.start} → ${data.meta.end} · run ${data.meta.run_date}` : "Per-trade results of every setup and exit rule."}</p></div>
      <button className="btn primary" disabled=${busy} onClick=${rerun}>${busy ? "Running…" : "Re-run backtest"}</button>
    </div>
    <div className="note">Current NIFTY 500 members only, so stocks that dropped out are missing (survivorship bias — results are flattered, most of all the long-term setup in 2023). The breadth gate was chosen on this same data. Net = after slippage and delivery charges on ₹1 lakh per trade.</div>
    <${ErrorBox} err=${err} />
    ${loading && !data ? html`<${Loading} />` : null}
    ${data ? html`
      <div className="row" style=${{ marginBottom: "10px" }}>
        <select className="input" value=${view} onChange=${(e) => setView(e.target.value)}>
          ${VIEWS.map(([k, l]) => html`<option key=${k} value=${k}>${l}</option>`)}
        </select>
        <span className="faint">PF: <span className="up">≥1.3 good</span> · <span className="muted">1.0–1.3 thin</span> · <span className="down">${"<1 losing"}</span></span>
      </div>
      <div className="tbl-wrap"><table>
        <thead><tr><th>Setup</th><th>Horizon</th><th>Exit</th><th className="num">Trades</th><th className="num">Win</th><th className="num">Avg net</th>
          <th className="num">PF</th><th className="num">Avg R</th><th className="num">Avg days</th><th className="num">Charges</th><th className="num">Open now</th></tr></thead>
        <tbody>${res.map((r) => html`<tr key=${r.setup + r.policy}>
          <td><b>${data.setups?.[r.setup]?.label || r.setup}</b><div className="faint" style=${{ fontSize: "11px" }}>${r.setup}</div></td>
          <td className="muted">${r.horizon}</td><td>${r.policy}</td>
          <${Cells} s=${r[view]} /><td className="num">${r.open_now}</td></tr>`)}</tbody>
      </table></div>
      <h2 style=${{ fontSize: "16px", margin: "26px 0 10px" }}>By signal year</h2>
      ${res.map((r) => html`
        <details key=${r.setup + r.policy} className="panel" style=${{ marginBottom: "8px", padding: "8px 14px" }}>
          <summary><b style=${{ color: "var(--text)" }}>${r.setup} / ${r.policy}</b> — exits: ${Object.entries(r.exits).map(([k, v]) => `${k} ${v}`).join(", ")}</summary>
          <div className="tbl-wrap" style=${{ margin: "8px 0" }}><table>
            <thead><tr><th>Year</th><th className="num">Trades</th><th className="num">Win</th><th className="num">Avg net</th><th className="num">PF</th><th className="num">Avg R</th><th className="num">Avg days</th><th className="num">Charges</th></tr></thead>
            <tbody>${Object.entries(r.by_year).map(([y, s]) => html`<tr key=${y}><td>${y}</td><${Cells} s=${s} /></tr>`)}</tbody>
          </table></div>
        </details>`)}
      <h2 style=${{ fontSize: "16px", margin: "26px 0 10px" }}>Definitions</h2>
      <div className="grid2">
        <div className="panel"><h3>Setups</h3>${Object.entries(data.setups || {}).map(([k, s]) => html`<p key=${k} style=${{ margin: "0 0 10px" }}><b>${s.label}</b> <span className="faint">(${s.horizon})</span><br /><span className="muted">${s.rule}</span></p>`)}</div>
        <div className="panel"><h3>Exit rules</h3>${Object.entries(data.policies || {}).map(([k, d]) => html`<p key=${k} style=${{ margin: "0 0 10px" }}><b>${k}</b><br /><span className="muted">${d}</span></p>`)}</div>
      </div>` : null}
    ${toast}`;
}
