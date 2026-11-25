import { html, useState, useEffect, api, useApi, Loading, ErrorBox, useToast } from "../lib.js";

const MAIN = [
  ["breadth_threshold_pct", "Market breadth gate (%)", "Below this share of NIFTY 500 above their own 50-day SMA, every signal stays Watch. Re-run the backtest after changing it", 1],
  ["min_pf", "Minimum setup PF to consider", "The setup's backtest profit factor in the current breadth state must reach this", 0.05],
  ["min_trades", "Minimum backtest trades", "A setup needs at least this many past trades before it can be considered", 10],
  ["slippage_pct", "Slippage per side (%)", "Used by the backtest. Re-run it after changing", 0.01],
];
const SIZE = [
  ["capital", "Capital (₹)", "Used to size every position", 1000],
  ["risk_pct", "Risk per trade (% of capital)", "What you lose if the stop is hit. Quantity = risk ÷ (entry − stop)", 0.1],
  ["max_position_pct", "Largest position (% of capital)", "Caps the quantity when the stop is very tight", 1],
];
const CHG = [
  ["stt_pct", "STT (% both sides)"], ["exch_pct", "Exchange txn (% both sides)"], ["sebi_pct", "SEBI (% both sides)"],
  ["stamp_buy_pct", "Stamp duty (% buy side)"], ["gst_pct", "GST (% on brokerage+exchange+SEBI)"],
  ["brokerage_pct", "Brokerage (% both sides)"], ["dp_per_sell", "DP charge per sell (₹)"],
];

export default function Settings() {
  const { data, err, loading } = useApi("/settings");
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(null);
  const [toast, show] = useToast();
  useEffect(() => { if (data) setS(data); }, [data]);
  if (loading && !s) return html`<${Loading} />`;
  if (!s) return html`<${ErrorBox} err=${err} />`;
  const set = (k, v) => setS({ ...s, [k]: v });
  const setC = (k, v) => setS({ ...s, charges: { ...s.charges, [k]: v } });
  const save = async (thenBacktest) => {
    setBusy(thenBacktest ? "Re-running backtest…" : "Saving…");
    try {
      setS(await api("/settings", { method: "PUT", body: s }));
      if (thenBacktest) { const m = await api("/backtest/run", { method: "POST" }); show(`Saved. Backtest re-run: ${m.trades} trades`); }
      else { await api("/scan/run", { method: "POST" }); show("Saved. Plans and quantities updated"); }
    } catch (e) { show("Failed: " + e.message); }
    setBusy(null);
  };
  return html`
    <div className="head">
      <div><h1>Settings</h1><p>Saved in the app, in data/settings.json</p></div>
      <div className="row">
        <button className="btn" disabled=${!!busy} onClick=${() => save(false)}>Save</button>
        <button className="btn primary" disabled=${!!busy} onClick=${() => save(true)}>${busy || "Save and re-run backtest"}</button>
      </div>
    </div>
    <div className="panel" style=${{ marginBottom: "12px" }}>
      <h3>Signals</h3>
      <div className="form">
        ${MAIN.map(([k, label, help, step]) => html`
          <label key=${k + "l"}>${label}</label>
          <input key=${k + "i"} className="input" type="number" step=${step} value=${s[k]} onInput=${(e) => set(k, e.target.value)} />
          <span key=${k + "h"} className="help">${help}</span>`)}
      </div>
    </div>
    <div className="panel" style=${{ marginBottom: "12px" }}>
      <h3>Position sizing</h3>
      <div className="form">
        ${SIZE.map(([k, label, help, step]) => html`
          <label key=${k + "l"}>${label}</label>
          <input key=${k + "i"} className="input" type="number" step=${step} value=${s[k]} onInput=${(e) => set(k, e.target.value)} />
          <span key=${k + "h"} className="help">${help}</span>`)}
      </div>
    </div>
    <div className="panel">
      <h3>Delivery charges</h3>
      <div className="form">
        ${CHG.map(([k, label]) => html`
          <label key=${k + "l"}>${label}</label>
          <input key=${k + "i"} className="input" type="number" step="0.0001" value=${s.charges[k]} onInput=${(e) => setC(k, e.target.value)} />
          <span key=${k + "h"} className="help"></span>`)}
      </div>
      <p className="muted" style=${{ fontSize: "12px", margin: "16px 0 0" }}>Approximate Zerodha-style delivery charges. Check them against one of your contract notes</p>
    </div>
    ${toast}`;
}
