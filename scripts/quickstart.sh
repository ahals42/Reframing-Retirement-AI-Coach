#!/usr/bin/env bash
#Use this from the repo root, e.g., cd <repo>/Reframing-Retirement && ./scripts/quickstart.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Allow override via env; defaults to the known-good 3.13 install.
PYTHON_BIN="${PYTHON_BIN:-/Library/Frameworks/Python.framework/Versions/3.13/bin/python3}"

if [ ! -d ".venv" ]; then
  echo "[setup] Creating virtual environment with ${PYTHON_BIN}"
  "${PYTHON_BIN}" -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".venv/.deps-installed" ]; then
  echo "[setup] Installing Python dependencies"
  pip install -r requirements.txt
  touch .venv/.deps-installed
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[error] Docker command not found. Install Docker Desktop first." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[error] Docker daemon is not running. Start Docker Desktop and rerun." >&2
  exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -qx "rr-qdrant"; then
  if ! docker start rr-qdrant >/dev/null 2>&1; then
    echo "[setup] Existing rr-qdrant container failed to start; removing and recreating."
    docker rm -f rr-qdrant >/dev/null
  fi
fi

if ! docker ps -a --format '{{.Names}}' | grep -qx "rr-qdrant"; then
  echo "[setup] Creating rr-qdrant container with persistent storage"
  docker run --name rr-qdrant \
    -v "${REPO_ROOT}/qdrant_storage":/qdrant/storage \
    -p 6333:6333 -p 6334:6334 \
    -d qdrant/qdrant
fi

echo "[wait] Checking Qdrant health..."
until curl -fsS http://localhost:6333/healthz >/dev/null 2>&1; do
  sleep 1
done

MODE="${QUICKSTART_MODE:-${1:-cli}}"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"

case "${MODE}" in
  cli)
    echo "[run] Starting conversational agent (CLI)"
    python main.py
    ;;
  api)
    echo "[run] Starting FastAPI server at http://${API_HOST}:${API_PORT}"
    uvicorn backend.app:app --host "${API_HOST}" --port "${API_PORT}"
    ;;
  *)
    echo "[error] Unknown mode '${MODE}'. Use 'cli' or 'api'." >&2
    exit 1
    ;;
esac
