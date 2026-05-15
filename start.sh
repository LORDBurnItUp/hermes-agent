#!/usr/bin/env bash
# start.sh — Launch the full Swarm OS stack.
#
# Starts:
#   1. FastAPI backend  (uvicorn swarm.server:app) on http://localhost:8000
#   2. React Vite dev   (npm --prefix dashboard run dev)  on http://localhost:5174
#
# Usage:
#   ./start.sh           # dry-run mode (no real API keys needed)
#   ./start.sh --live    # hit real APIs (set env vars first)

set -euo pipefail

BACKEND_PORT=8000
FRONTEND_PORT=5174

# Install dashboard dependencies if node_modules is absent.
if [ ! -d "dashboard/node_modules" ]; then
  echo "[swarm] Installing dashboard dependencies..."
  npm --prefix dashboard install
fi

cleanup() {
  echo ""
  echo "[swarm] Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  echo "[swarm] Done."
}
trap cleanup INT TERM EXIT

echo "[swarm] Starting FastAPI backend on http://localhost:${BACKEND_PORT} ..."
uvicorn swarm.server:app \
  --host 0.0.0.0 \
  --port "$BACKEND_PORT" \
  --reload \
  --log-level info &
BACKEND_PID=$!

echo "[swarm] Starting React Vite dev server on http://localhost:${FRONTEND_PORT} ..."
npm --prefix dashboard run dev &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SWARM OS IS RUNNING"
echo "  Backend  → http://localhost:${BACKEND_PORT}"
echo "  Dashboard → http://localhost:${FRONTEND_PORT}"
echo "  SSE feed  → http://localhost:${BACKEND_PORT}/swarm/events"
echo "  Trigger   → POST http://localhost:${BACKEND_PORT}/swarm/run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Press Ctrl+C to stop all processes."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

wait "$BACKEND_PID" "$FRONTEND_PID"
