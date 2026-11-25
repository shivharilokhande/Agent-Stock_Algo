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
export const pfCls = (pf) => (pf == null ? "faint" : pf >= 1.3 ? "up" : pf >= 1.0 ? "muted" : "down");
export const go = (hash) => { location.hash = hash; };

const BADGE = { CONSIDER: "b-green", WATCH: "b-grey", EXIT: "b-red", TIGHTEN: "b-amber", HOLD: "b-green", UNKNOWN: "b-grey" };
export const Badge = ({ v }) => html`<span className=${"badge " + (BADGE[v] || "b-grey")}>${v}</span>`;

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
