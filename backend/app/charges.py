"""Indian equity DELIVERY charges for one round trip (buy then sell)."""
from .config import CHARGES


def round_trip(buy_value, sell_value, ch=None):
    ch = ch or CHARGES
    turnover = buy_value + sell_value
    brokerage = turnover * ch["brokerage_pct"] / 100
    stt = turnover * ch["stt_pct"] / 100
    exch = turnover * ch["exch_pct"] / 100
    sebi = turnover * ch["sebi_pct"] / 100
    stamp = buy_value * ch["stamp_buy_pct"] / 100
    gst = (brokerage + exch + sebi) * ch["gst_pct"] / 100
    return brokerage + stt + exch + sebi + stamp + gst + ch["dp_per_sell"]
