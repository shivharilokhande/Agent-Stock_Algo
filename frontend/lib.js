import React, { useState, useEffect, useCallback, useRef, useMemo } from "https://esm.sh/react@18.3.1";
import htm from "https://esm.sh/htm@3.1.1";

export const html = htm.bind(React.createElement);
export { React, useState, useEffect, useCallback, useRef, useMemo };

export async function api(path, opts = {}) {
  const init = { method: opts.method || "GET", headers: { "Content-Type": "application/json" } };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
  const r = await fetch("/api" + path, init);
  const text = await r.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (!r.ok) throw new Error((data && data.detail) || r.statusText);
  return data;
}

export function useApi(path) {
  const [state, set] = useState({ data: null, err: null, loading: true });
  const load = useCallback(async () => {
    set((s) => ({ ...s, loading: true, err: null }));
    try { set({ data: await api(path), err: null, loading: false }); }
    catch (e) { set({ data: null, err: e.message, loading: false }); }
  }, [path]);
  useEffect(() => { load(); }, [load]);
  return { ...state, reload: load, setData: (d) => set({ data: d, err: null, loading: false }) };
}

export const num = (v, d = 2) =>
  v == null || Number.isNaN(v) ? "—" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
export const pct = (v, d = 1, sign = true) =>
  v == null || Number.isNaN(v) ? "—" : `${sign && v > 0 ? "+" : ""}${Number(v).toFixed(d)}%`;
export const cls = (v) => (v == null ? "" : v > 0 ? "up" : v < 0 ? "down" : "");
export const pfCls = (pf) => (pf == null ? "muted" : pf >= 1.2 ? "up" : pf >= 1.0 ? "sec" : "down");
export const day = (iso) => (iso ? new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—");
export const go = (hash) => { location.hash = hash; };

const TAG = { CONSIDER: "t-pos", WATCH: "t-quiet", EXIT: "t-neg", TIGHTEN: "t-warn", HOLD: "t-quiet", UNKNOWN: "t-quiet" };
const WORD = { CONSIDER: "Consider", WATCH: "Watch", EXIT: "Exit", TIGHTEN: "Tighten", HOLD: "Hold", UNKNOWN: "Unknown" };
export const Badge = ({ v }) => html`<span className=${"tag " + (TAG[v] || "t-quiet")}>${WORD[v] || v}</span>`;

/* Signature: a bar with a threshold tick. value/min on the same scale; max caps the bar. */
export function Track({ value, min, max, small = false, title }) {
  const w = value == null ? 0 : Math.max(0, Math.min(1, value / max)) * 100;
  const color = value == null ? "var(--raised)" : value >= min ? "var(--pos)" : value >= min * 0.85 ? "var(--text-2)" : "var(--neg)";
  return html`<span className=${"track" + (small ? " sm" : "")} title=${title || ""}>
    <i style=${{ width: w + "%", background: color }}></i><b style=${{ left: (min / max) * 100 + "%" }}></b></span>`;
}
export function PfBar({ pf, min = 1.2 }) {
  return html`<span className="pf"><${Track} value=${pf} min=${min} max=${2.5} small=${true} title=${`PF ${pf ?? "—"} · line at ${min}`} />
    <span className=${pfCls(pf)}>${pf ?? "—"}</span></span>`;
}

export function Loading({ what = "Loading" }) { return html`<div className="empty">${what}…</div>`; }
export function ErrorBox({ err }) { return err ? html`<div className="err">${err}</div>` : null; }

export function useToast() {
  const [msg, setMsg] = useState(null);
  const show = useCallback((m) => { setMsg(m); setTimeout(() => setMsg(null), 3500); }, []);
  const node = msg ? html`<div className="toast">${msg}</div>` : null;
  return [node, show];
}

export function useUniverse() {
  const { data } = useApi("/universe");
  return data || [];
}
