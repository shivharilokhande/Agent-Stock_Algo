"""AgentStockAlgo settings. Separate from AgentAlgo: own folder, own DB, own ports."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DATA = BACKEND / "data"
DATA.mkdir(parents=True, exist_ok=True)
DOCS = ROOT / "docs"
STUDIES = DOCS / "studies"
STUDIES.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA / "agentstockalgo.db"
HOLDINGS_FILE = DATA / "holdings.json"      # your positions for the exit board
SCAN_FILE = DATA / "scan_latest.json"
EXITS_FILE = DATA / "exits_latest.json"
BT_SUMMARY_FILE = DATA / "backtest_summary.json"
BT_TRADES_FILE = DATA / "backtest_trades.csv"

API_PORT = 8100                              # AgentAlgo uses 8000 / 5180

# Universe + data (free sources only; Kite is NOT used so AgentAlgo's session is never touched)
UNIVERSE_URL = "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv"
BENCHMARK = "^CRSLDX"                        # NIFTY 500 index (regime + relative strength)
NIFTY = "^NSEI"
HISTORY_PERIOD = "5y"
DOWNLOAD_CHUNK = 50

# Equity DELIVERY charges (approximate Zerodha-style; verify against your contract note).
# % values are percent of turnover on that side.
CHARGES = {
    "brokerage_pct": 0.0,       # delivery brokerage
    "stt_pct": 0.10,            # buy and sell
    "exch_pct": 0.00297,        # NSE transaction charge, both sides
    "sebi_pct": 0.0001,         # Rs 10 / crore, both sides
    "stamp_buy_pct": 0.015,     # buy side only
    "gst_pct": 18.0,            # on brokerage + exchange + SEBI
    "dp_per_sell": 15.93,       # DP charge per scrip per sell day (incl GST)
}
SLIPPAGE_PCT = 0.10             # per side, % of price
TRADE_NOTIONAL = 100_000        # Rs per trade used for charge and P&L stats
MIN_RISK_PCT = 1.0              # stop is at least 1% below entry (avoids fake huge R)
