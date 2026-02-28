#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# Redline — Start vLLM model server + FastAPI backend
# Usage:
#   ./start.sh                      # auto-detect model path
#   ./start.sh /path/to/model       # explicit model path
#   ./start.sh --api-only           # skip vLLM, use Mistral API
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load env vars (.env file)
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "[ok] Loaded .env"
fi

# ── Defaults ─────────────────────────────────────────────────
VLLM_HOST="${VLLM_HOST:-0.0.0.0}"
VLLM_PORT="${VLLM_PORT:-8080}"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
GPU_UTIL="${GPU_UTIL:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
API_ONLY=false

# ── Parse args ───────────────────────────────────────────────
MODEL_PATH=""
for arg in "$@"; do
    case "$arg" in
        --api-only)
            API_ONLY=true
            ;;
        *)
            MODEL_PATH="$arg"
            ;;
    esac
done

# ── Cleanup on exit ──────────────────────────────────────────
cleanup() {
    echo ""
    echo "[info] Shutting down..."
    # Kill background jobs (vLLM)
    jobs -p | xargs -r kill 2>/dev/null || true
    wait 2>/dev/null || true
    echo "[ok] Stopped."
}
trap cleanup EXIT INT TERM

# ── Start vLLM ───────────────────────────────────────────────
if [ "$API_ONLY" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  API-only mode — using Mistral API, no vLLM"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    export REDLINE_USE_MISTRAL_API=true
else
    # Auto-detect model path if not provided
    if [ -z "$MODEL_PATH" ]; then
        # Check common locations
        for candidate in \
            "./outputs/redline-mistral-merged" \
            "./outputs/redline-mistral-lora/merged" \
            "./outputs/merged_model" \
            "$HOME/models/redline-mistral" \
            "$HOME/redline-mistral-merged"; do
            if [ -d "$candidate" ] && [ -f "$candidate/config.json" ]; then
                MODEL_PATH="$candidate"
                break
            fi
        done
    fi

    if [ -z "$MODEL_PATH" ] || [ ! -d "$MODEL_PATH" ]; then
        echo "ERROR: Could not find model. Provide the path as an argument:"
        echo "  ./start.sh /path/to/merged/model"
        echo ""
        echo "Or use API-only mode:"
        echo "  ./start.sh --api-only"
        exit 1
    fi

    MODEL_PATH="$(cd "$MODEL_PATH" && pwd)"  # absolute path
    export REDLINE_MODEL_ENDPOINT="http://localhost:${VLLM_PORT}"
    export REDLINE_USE_MISTRAL_API=false

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Starting vLLM inference server"
    echo "  Model:  $MODEL_PATH"
    echo "  Listen: ${VLLM_HOST}:${VLLM_PORT}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL_PATH" \
        --host "$VLLM_HOST" \
        --port "$VLLM_PORT" \
        --tensor-parallel-size 1 \
        --max-model-len "$MAX_MODEL_LEN" \
        --gpu-memory-utilization "$GPU_UTIL" \
        --guided-decoding-backend outlines \
        2>&1 | while IFS= read -r line; do echo "[vllm] $line"; done &

    VLLM_PID=$!
    echo "[info] vLLM PID: $VLLM_PID"

    # Wait for vLLM to be ready
    echo "[info] Waiting for vLLM to be ready..."
    MAX_WAIT=120
    WAITED=0
    while ! curl -s "http://localhost:${VLLM_PORT}/health" > /dev/null 2>&1; do
        if ! kill -0 "$VLLM_PID" 2>/dev/null; then
            echo "ERROR: vLLM process exited unexpectedly."
            exit 1
        fi
        sleep 2
        WAITED=$((WAITED + 2))
        if [ "$WAITED" -ge "$MAX_WAIT" ]; then
            echo "ERROR: vLLM did not become ready within ${MAX_WAIT}s."
            exit 1
        fi
    done
    echo "[ok] vLLM is ready (took ${WAITED}s)"
fi

# ── Start FastAPI ────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Starting FastAPI server"
echo "  Listen: ${API_HOST}:${API_PORT}"
echo "  Docs:   http://localhost:${API_PORT}/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python -m uvicorn api.server:app \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --reload
