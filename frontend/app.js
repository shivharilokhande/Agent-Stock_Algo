import { html, useState, useEffect, api } from "./lib.js";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import Today from "./pages/today.js";
import Exits from "./pages/exits.js";
import Stock from "./pages/stock.js";
import Backtest from "./pages/backtest.js";
import Settings from "./pages/settings.js";

const NAV = [
  ["today", "Today", "M3 12h4l3-8 4 16 3-8h4"],
  ["exits", "Exits", "M15 3h6v6M10 14L21 3M21 14v7H3V3h7"],
  ["stock", "Stock", "M3 3v18h18M7 15l4-4 3 3 6-7"],
  ["backtest", "Backtest", "M4 19V9M10 19V5M16 19v-7M22 19H2"],
  ["settings", "Settings", "M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-2.9 1.2V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-2.9-1.2l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00-1.2-2.9H3a2 2 0 110-4h.1a1.7 1.7 0 001.2-2.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 002.9-1.2V3a2 2 0 114 0v.1a1.7 1.7 0 002.9 1.2l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 001.2 2.9H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"],
];

function route() {
  const h = (location.hash || "#/today").replace(/^#\/?/, "");
  const [page, ...rest] = h.split("/");
  return { page: page || "today", arg: decodeURIComponent(rest.join("/") || "") };
}

function Icon({ d }) {
  return html`<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d=${d} /></svg>`;
}

function App() {
  const [r, setR] = useState(route());
  const [exitCount, setExitCount] = useState(0);
  const [health, setHealth] = useState(null);
  useEffect(() => {
    const on = () => setR(route());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    api("/health").then(setHealth).catch(() => {});
    api("/exits").then((d) => setExitCount((d.holdings || []).filter((h) => h.action === "EXIT").length)).catch(() => {});
  }, [r.page]);
  const pages = { today: Today, exits: Exits, stock: Stock, backtest: Backtest, settings: Settings };
  const Page = pages[r.page] || Today;
  return html`
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <div className="mark"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 18L10 11l4 4 6-8" /><path d="M3 12h18" strokeOpacity=".45" strokeDasharray="2 3" /></svg></div>
          <span>AgentStockAlgo</span>
        </div>
        <nav className="nav">
          ${NAV.map(([k, label, d]) => html`
            <a key=${k} href=${"#/" + k} className=${r.page === k ? "on" : ""}>
              <${Icon} d=${d} /> ${label}
              ${k === "exits" && exitCount > 0 ? html`<span className="count">${exitCount}</span>` : null}
            </a>`)}
        </nav>
        <div className="side-foot">
          <p>${health ? `Prices ${(health.last_ingest || "—").replace("T", " ").slice(0, 16)}` : "API offline"}</p>
          <p>Recommendations only, no orders</p>
        </div>
      </aside>
      <main className="main"><${Page} arg=${r.arg} /></main>
    </div>`;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
