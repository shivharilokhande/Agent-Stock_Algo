import { html, useState, useEffect, api, useApi, num, pct, cls, Badge, Loading, ErrorBox, useToast, useUniverse } from "../lib.js";

const BLANK = { symbol: "", qty: "", avg_price: "", buy_date: "", horizon: "swing" };

function Editor({ onSaved, show }) {
  const { data, err } = useApi("/holdings");
  const uni = useUniverse();
  const [rows, setRows] = useState([]);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (data) setRows(data.map((r) => ({ ...BLANK, ...r, qty: r.qty ?? "", buy_date: r.buy_date ?? "" }))); }, [data]);
  const upd = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const save = async () => {
    const clean = rows.filter((r) => r.symbol && r.avg_price).map((r) => ({
      ...r, symbol: r.symbol.toUpperCase().trim(), qty: r.qty === "" ? null : Number(r.qty), avg_price: Number(r.avg_price) }));
    setSaving(true);
    try { onSaved(await api("/holdings", { method: "PUT", body: clean })); show(`Saved ${clean.length} holdings`); }
    catch (e) { show("Save failed: " + e.message); }
    setSaving(false);
  };
  return html`
    <div className="panel" style=${{ marginTop: "18px" }}>
      <h3>Your holdings</h3>
      <${ErrorBox} err=${err} />
      <datalist id="syms">${uni.map((u) => html`<option key=${u.symbol} value=${u.symbol}>${u.name}</option>`)}</datalist>
      <div className="tbl-wrap">
        <table>
          <thead><tr><th>Symbol</th><th>Qty</th><th>Avg price</th><th>Buy date</th><th>Horizon</th><th></th></tr></thead>
          <tbody>
            ${rows.map((r, i) => html`
              <tr key=${i}>
                <td><input className="input" list="syms" value=${r.symbol} onInput=${(e) => upd(i, "symbol", e.target.value.toUpperCase())} placeholder="TCS" /></td>
                <td><input className="input" type="number" value=${r.qty} onInput=${(e) => upd(i, "qty", e.target.value)} /></td>
                <td><input className="input" type="number" step="0.05" value=${r.avg_price} onInput=${(e) => upd(i, "avg_price", e.target.value)} /></td>
                <td><input className="input" type="date" value=${r.buy_date || ""} onInput=${(e) => upd(i, "buy_date", e.target.value)} /></td>
                <td><select className="input" value=${r.horizon} onChange=${(e) => upd(i, "horizon", e.target.value)}>
                  <option value="swing">Swing</option><option value="long">Long-term</option></select></td>
                <td><button className="btn danger" onClick=${() => setRows(rows.filter((_, j) => j !== i))}>Remove</button></td>
              </tr>`)}
          </tbody>
        </table>
      </div>
      <div className="row" style=${{ marginTop: "12px" }}>
        <button className="btn" onClick=${() => setRows([...rows, { ...BLANK }])}>+ Add holding</button>
        <button className="btn primary" disabled=${saving} onClick=${save}>${saving ? "Saving…" : "Save and re-check"}</button>
        <span className="faint">Swing: 2×ATR stop under cost, then 3×ATR trail off the highest close. Long: 15% stop, exit on a close below SMA150.</span>
      </div>
    </div>`;
}

export default function Exits() {
  const { data, err, loading, setData } = useApi("/exits");
  const [toast, show] = useToast();
  const hs = data?.holdings || [];
  const counts = ["EXIT", "TIGHTEN", "HOLD"].map((a) => [a, hs.filter((h) => h.action === a).length]);
  return html`
    <div className="head">
      <div><h1>Exit board</h1><p>What to do with what you already hold, from the latest daily close.</p></div>
      <div className="row">${counts.map(([a, n]) => html`<span key=${a} className="row"><${Badge} v=${a} /> <b className="mono">${n}</b></span>`)}</div>
    </div>
    <${ErrorBox} err=${err} />
    ${loading && !data ? html`<${Loading} />` : null}
    ${hs.length ? html`
      <div className="tbl-wrap">
        <table>
          <thead><tr><th>Action</th><th>Symbol</th><th>Horizon</th><th className="num">Qty</th><th className="num">Avg</th>
            <th className="num">Close</th><th className="num">P&L</th><th className="num">Stop level</th><th>Why</th></tr></thead>
          <tbody>${hs.map((h) => html`
            <tr key=${h.symbol + h.horizon}>
              <td><${Badge} v=${h.action} /></td>
              <td><a href=${"#/stock/" + h.symbol}><b>${h.symbol}</b></a></td>
              <td className="muted">${h.horizon || "—"}</td>
              <td className="num">${h.qty ?? "—"}</td>
              <td className="num">${num(h.avg_price)}</td>
              <td className="num">${num(h.close)}</td>
              <td className=${"num " + cls(h.pnl_pct)}>${pct(h.pnl_pct, 2)}</td>
              <td className="num">${num(h.stop_level)}</td>
              <td style=${{ whiteSpace: "normal", minWidth: "260px" }}>${(h.reasons || []).join("; ")}</td>
            </tr>`)}</tbody>
        </table>
      </div>
      <div className="faint" style=${{ fontSize: "12px", marginTop: "8px" }}>Checked ${(data.generated || "").replace("T", " ")}. Stop levels are on the daily close.</div>`
      : !loading ? html`<div className="empty">No holdings yet — add them below.</div>` : null}
    <${Editor} onSaved=${setData} show=${show} />
    ${toast}`;
}
