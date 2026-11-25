import { html, useState, api, useApi, pct, pfCls, PfBar, Loading, ErrorBox, useToast } from "../lib.js";

const VIEWS = [
  ["all", "All trades"], ["breadth_on", "Breadth ON"], ["breadth_off", "Breadth OFF"],
  ["breadth_on_last_40", "Breadth ON · recent 40%"], ["breadth_off_last_40", "Breadth OFF · recent 40%"],
  ["first_60", "First 60%"], ["last_40", "Recent 40%"], ["regime_on", "NIFTY500 > 200 SMA"], ["regime_off", "NIFTY500 < 200 SMA"],
];

function Cells({ s }) {
  if (!s || !s.trades) return html`<td className="num muted" colSpan="7">no trades</td>`;
  return html`
    <td className="num">${s.trades}</td>
    <td className="num">${s.win_pct}%</td>
    <td className=${"num " + (s.avg_net_pct > 0 ? "up" : "down")}>${pct(s.avg_net_pct, 2)}</td>
    <td className="num"><${PfBar} pf=${s.pf} /></td>
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
      <div><h1>Backtest</h1><p>${data ? `${data.meta.stocks} NIFTY 500 stocks · ${data.meta.start} to ${data.meta.end} · run ${data.meta.run_date}` : "Per-trade results of every setup and exit rule"}</p></div>
      <button className="btn primary" disabled=${busy} onClick=${rerun}>${busy ? "Running…" : "Re-run backtest"}</button>
    </div>
    <div className="note">Uses today's NIFTY 500 members, so stocks that dropped out are missing and results are flattered, most of all the long-term setup in 2023. The breadth gate was chosen on this same data. Net figures are after slippage and delivery charges on ₹1 lakh per trade</div>
    <${ErrorBox} err=${err} />
    ${loading && !data ? html`<${Loading} />` : null}
    ${data ? html`
      <div className="row" style=${{ marginBottom: "16px" }}>
        <select className="input" value=${view} onChange=${(e) => setView(e.target.value)}>
          ${VIEWS.map(([k, l]) => html`<option key=${k} value=${k}>${l}</option>`)}
        </select>
        <span className="muted" style=${{ fontSize: "12px" }}>The tick on each PF bar is the 1.2 needed to be considered</span>
      </div>
      <div className="tbl-wrap"><table>
        <thead><tr><th>Setup</th><th>Horizon</th><th>Exit</th><th className="num">Trades</th><th className="num">Win</th><th className="num">Avg net</th>
          <th className="num">PF</th><th className="num">Avg R</th><th className="num">Avg days</th><th className="num">Charges</th><th className="num">Open now</th></tr></thead>
        <tbody>${res.map((r) => html`<tr key=${r.setup + r.policy}>
          <td>${data.setups?.[r.setup]?.label || r.setup}<div className="muted mono">${r.setup}</div></td>
          <td className="muted">${r.horizon}</td><td>${r.policy}</td>
          <${Cells} s=${r[view]} /><td className="num">${r.open_now}</td></tr>`)}</tbody>
      </table></div>
      <h2 className="section-title section">By signal year</h2>
      ${res.map((r) => html`
        <details key=${r.setup + r.policy} className="panel">
          <summary><b>${data.setups?.[r.setup]?.label || r.setup} · ${r.policy}</b> <span className="muted mono">exits</span> ${Object.entries(r.exits).map(([k, v]) => `${k} ${v}`).join(", ")}</summary>
          <div className="tbl-wrap"><table>
            <thead><tr><th>Year</th><th className="num">Trades</th><th className="num">Win</th><th className="num">Avg net</th><th className="num">PF</th><th className="num">Avg R</th><th className="num">Avg days</th><th className="num">Charges</th></tr></thead>
            <tbody>${Object.entries(r.by_year).map(([y, s]) => html`<tr key=${y}><td>${y}</td><${Cells} s=${s} /></tr>`)}</tbody>
          </table></div>
        </details>`)}
      <h2 className="section-title section">Definitions</h2>
      <div className="grid2">
        <div className="panel defs"><h3>Setups</h3>${Object.entries(data.setups || {}).map(([k, s]) => html`<p key=${k}><b>${s.label} · ${s.horizon}</b>${s.rule}</p>`)}</div>
        <div className="panel defs"><h3>Exit rules</h3>${Object.entries(data.policies || {}).map(([k, d]) => html`<p key=${k}><b>${k}</b>${d}</p>`)}</div>
      </div>` : null}
    ${toast}`;
}
