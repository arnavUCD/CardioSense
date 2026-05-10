#!/usr/bin/env bash
# CardioSense — start the full hackathon demo pipeline.
#
#   Stage 1 (signal sim) -> Stage 2 (clean/peaks/HRV) -> ML watcher -> HTTP server
#
# Stop everything with Ctrl+C (the trap below kills all background children).
set -u
cd "$(dirname "$0")"

VENV_PY="$(pwd)/.venv/bin/python"
LOG_DIR="$(pwd)/logs"
mkdir -p "$LOG_DIR"

if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: $VENV_PY not found. Did you run 'python3.10 -m venv .venv'?"
  exit 1
fi

pids=()
cleanup() {
  echo
  echo "[demo] stopping all stages..."
  for pid in "${pids[@]:-}"; do
    [[ -n "$pid" ]] && kill -TERM "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null
  echo "[demo] all stopped."
}
trap cleanup INT TERM EXIT

echo "[demo] Mac LAN IP for the iPhone: $(ipconfig getifaddr en0 2>/dev/null || echo '<unknown>')"
echo "[demo] iOS app should hit:        http://$(ipconfig getifaddr en0 2>/dev/null || echo 10.0.0.29):8080/shared/prediction.json"
echo "[demo] logs -> $LOG_DIR/"
echo

# Stage 1: simulated BLE ECG stream
( cd SignalGenerator/stage1 && PYTHONPATH=. "$VENV_PY" -u main.py ) \
  > "$LOG_DIR/stage1.log" 2>&1 &
pid=$!; pids+=("$pid")
echo "[demo] Stage 1 (signal sim)  pid=$pid"

# Stage 2: clean signal + R-peaks + HRV -> writes input.json
( cd SignalGenerator/stage2 && PYTHONPATH=. "$VENV_PY" -u stage2.py ) \
  > "$LOG_DIR/stage2.log" 2>&1 &
pid=$!; pids+=("$pid")
echo "[demo] Stage 2 (cleaner)     pid=$pid"

# ML watcher: input.json -> prediction.json
( "$VENV_PY" -u watch_and_predict.py ) > "$LOG_DIR/watcher.log" 2>&1 &
pid=$!; pids+=("$pid")
echo "[demo] ML watcher            pid=$pid"

# Static HTTP server: serves prediction.json at /shared/prediction.json
( "$VENV_PY" -u -m http.server 8080 ) > "$LOG_DIR/http.log" 2>&1 &
pid=$!; pids+=("$pid")
echo "[demo] HTTP server :8080     pid=$pid"

echo
echo "[demo] all stages running. tailing watcher.log (Ctrl+C to stop everything)"
echo "----------------------------------------------------------------------"
# follow the watcher so the user can see ML output live; the others go to logs/
sleep 1
tail -F "$LOG_DIR/watcher.log"
