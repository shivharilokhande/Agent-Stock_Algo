#!/bin/zsh
# Start AgentStockAlgo (API + UI) on http://localhost:8100
cd "$(dirname "$0")/backend" || exit 1
exec ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8100
