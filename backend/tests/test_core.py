import numpy as np
import pandas as pd
import pytest

from app import backtest, charges
from app.indicators import features, rsi


def bars(closes, spread=1.0, opens=None):
    idx = pd.bdate_range("2024-01-01", periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    o = pd.Series(opens, index=idx, dtype=float) if opens is not None else c.shift(1).fillna(c.iloc[0])
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + spread, "low": np.minimum(o, c) - spread,
                         "close": c, "volume": 1e6})


def test_rsi_all_up_is_100():
    r = rsi(pd.Series(np.arange(1, 40, dtype=float)), 14)
    assert r.iloc[-1] == 100.0


def test_charges_round_trip():
    # 1L buy, 1L sell: STT 200 + exch 5.94 + SEBI 0.2 + stamp 15 + GST on (5.94+0.2) + DP 15.93
    v = charges.round_trip(100_000, 100_000)
    assert v == pytest.approx(200 + 5.94 + 0.2 + 15 + 6.14 * 0.18 + 15.93, rel=1e-3)


def _feat(df):
    return features(df).assign(regime=True, rs_pct=0.5)


def test_entry_next_open_and_stop():
    df = bars([100] * 30 + [101, 99, 90, 90])
    f = _feat(df)
    i = 30                          # signal on bar 30; entry at bar 31 open (=101 close of 30)
    tr = backtest.simulate(f, i, 98.0, "R2")
    assert tr["entry_date"] == f.index[31]
    assert tr["entry"] == pytest.approx(f["open"].iat[31] * 1.001)
    assert tr["reason"] == "STOP"


def test_gap_below_stop_fills_at_open():
    df = bars([100] * 30 + [100, 100, 80], opens=[100] * 32 + [80])
    f = _feat(df)
    tr = backtest.simulate(f, 30, 95.0, "R2")
    assert tr["reason"] == "STOP"
    assert tr["exit"] == pytest.approx(80 * 0.999)


def test_skip_when_open_below_stop():
    df = bars([100] * 31 + [90], opens=[100] * 31 + [90])
    assert backtest.simulate(_feat(df), 30, 95.0, "R2") is None


def test_target_hit():
    df = bars([100] * 31 + [100, 130], spread=0.5)
    tr = backtest.simulate(_feat(df), 30, 98.0, "R2")
    assert tr["reason"] == "TARGET"
    assert tr["net_r"] > 1.5


def test_time_exit():
    df = bars([100.0] * 60, spread=0.2)
    tr = backtest.simulate(_feat(df), 30, 90.0, "R2")
    assert tr["reason"] == "TIME"
    assert tr["days"] == 20
