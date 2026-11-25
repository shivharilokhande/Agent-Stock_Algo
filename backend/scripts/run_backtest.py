"""Run the backtest study. Usage: python scripts/run_backtest.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.study import run_study  # noqa: E402

if __name__ == "__main__":
    run_study()
