#!/usr/bin/env bash
# Fungal Cortex v2.0 — One-Click Startup (Bash)
# Usage: ./start.sh [--no-frontend] [--no-chroma] [--seed]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "  Fungal Cortex v2.0 — L6-Complete Agent OS"
echo "  One-Click Startup Launcher"
echo ""

# ── Check prerequisites ────────────────────────────────────────────────
echo "── Prerequisites ──"

python3 --version 2>/dev/null || python --version 2>/dev/null || {
    echo "  [FAIL] Python 3.10+ is required"
    exit 1
}
echo "  [OK] Python found"

node --version 2>/dev/null || {
    echo "  [FAIL] Node.js 18+ is required"
    exit 1
}
echo "  [OK] Node.js $(node --version)"

# ── Install Python deps ────────────────────────────────────────────────
echo ""
echo "── Python Dependencies ──"
pip install -e . --quiet 2>/dev/null && echo "  [OK] Python dependencies ready" || echo "  [WARN] pip install had issues (may already be installed)"

# ── Install Node deps ──────────────────────────────────────────────────
echo ""
echo "── Node.js Dependencies ──"
FRONTEND_DIR="$ROOT/cortex-frontend"
if [ -d "$FRONTEND_DIR/node_modules" ]; then
    echo "  [OK] Node modules already installed"
else
    echo "  [ .. ] Installing..."
    (cd "$FRONTEND_DIR" && npm install --legacy-peer-deps) && echo "  [OK] Node dependencies installed"
fi

# ── Start ChromaDB (optional) ──────────────────────────────────────────
if [ "${1:-}" != "--no-chroma" ] && [ "${2:-}" != "--no-chroma" ] && [ "${3:-}" != "--no-chroma" ]; then
    echo ""
    echo "── ChromaDB ──"
    if command -v docker &>/dev/null; then
        docker run -d --rm --name cortex-chromadb -p 8001:8000 chromadb/chroma:latest 2>/dev/null && \
            echo "  [OK] ChromaDB started on port 8001" || \
            echo "  [WARN] ChromaDB may already be running"
    else
        echo "  [WARN] Docker not found — skipping ChromaDB"
    fi
fi

# ── Start Backend ──────────────────────────────────────────────────────
echo ""
echo "── Backend (FastAPI) ──"
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --log-level info &
BACKEND_PID=$!
echo "  [OK] Backend started (PID $BACKEND_PID)"
sleep 2

# ── Start Frontend ─────────────────────────────────────────────────────
if [ "${1:-}" != "--no-frontend" ] && [ "${2:-}" != "--no-frontend" ] && [ "${3:-}" != "--no-frontend" ]; then
    echo ""
    echo "── Frontend (Next.js) ──"
    (cd "$FRONTEND_DIR" && npm run dev -- --port 3000) &
    FRONTEND_PID=$!
    echo "  [OK] Frontend started (PID $FRONTEND_PID)"
fi

# ── Seed skills ────────────────────────────────────────────────────────
if [ "${1:-}" = "--seed" ] || [ "${2:-}" = "--seed" ] || [ "${3:-}" = "--seed" ]; then
    echo ""
    echo "── Seed Skills ──"
    sleep 3
    python "$FRONTEND_DIR/scripts/seed_skills.py" --api-url http://localhost:8000 && \
        echo "  [OK] 22 demo skills imported" || \
        echo "  [WARN] Seed failed (backend may not be ready)"
fi

# ── Dashboard ──────────────────────────────────────────────────────────
echo ""
echo "  ==================================================="
echo "    All Services Ready!"
echo "  ==================================================="
echo ""
echo "    Backend API:  http://localhost:8000"
echo "    API Docs:     http://localhost:8000/docs"
echo "    Health:       http://localhost:8000/api/health"
echo "    Frontend:     http://localhost:3000"
echo ""
echo "    Press Ctrl+C to stop all services"
echo "  ==================================================="
echo ""

# ── Cleanup on exit ────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "── Shutting Down ──"
    [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null && echo "  [OK] Backend stopped"
    [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null && echo "  [OK] Frontend stopped"
    docker stop cortex-chromadb 2>/dev/null && echo "  [OK] ChromaDB stopped" || true
    echo ""
}

trap cleanup EXIT INT TERM

# Wait for any background process
wait
