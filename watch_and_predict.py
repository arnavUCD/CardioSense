"""File-based bridge between the signal-processing layer and the ML model.

Reads `SignalGenerator/stage2/shared/input.json` (written by Stage 2 of the
signal generator), runs the model, and writes
`shared/prediction.json` atomically (write to .tmp.json, then rename).

The iOS frontend fetches `shared/prediction.json` over a static HTTP
server (e.g. `python3 -m http.server 8080`), so we never crash, never
leave a half-written file, and never emit NaN/Infinity into JSON.

Run:
    .venv/bin/python watch_and_predict.py

Stop with Ctrl+C.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

from cardiosense.predict import predict_ecg

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

# Where the signal generator's Stage 2 writes its cleaned ECG window.
INPUT_PATH = PROJECT_ROOT / "SignalGenerator" / "stage2" / "shared" / "input.json"

# Where we write the prediction. The HTTP server serves the project root,
# so the iOS app fetches /shared/prediction.json.
SHARED_DIR = PROJECT_ROOT / "shared"
OUTPUT_PATH = SHARED_DIR / "prediction.json"
TMP_PATH = SHARED_DIR / "prediction.tmp.json"

POLL_SECONDS = 0.5  # how often to check input.json for changes


# ---------------------------------------------------------------------------
# Fallback prediction (returned if inference fails)
# ---------------------------------------------------------------------------
def _safe_error_prediction(error_msg: str) -> dict:
    return {
        "label": "Unknown",
        "confidence": 0.0,
        "probabilities": {"Normal": 0.0, "Arrhythmia": 0.0},
        "arrhythmia_detected": False,
        "heart_rate": None,
        "hrv": {
            "rmssd": None, "sdnn": None,
            "pnn50": None, "mean_rr_ms": None,
        },
        "sample_rate": 250,
        "window_seconds": 10,
        "n_windows": 0,
        "n_r_peaks": 0,
        "error": str(error_msg),
    }


# ---------------------------------------------------------------------------
# JSON sanitization: NaN / Infinity -> null
# ---------------------------------------------------------------------------
def _sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------
def _write_atomic(path: Path, payload: dict) -> None:
    """Write payload as JSON to a tmp file, then rename onto `path`.

    Rename is atomic on POSIX, so the iOS app never sees a half-written file.
    """
    safe = _sanitize_for_json(payload)
    text = json.dumps(safe, indent=2, allow_nan=False)
    TMP_PATH.write_text(text)
    os.replace(TMP_PATH, path)


# ---------------------------------------------------------------------------
# Input loading: tolerant to mid-write reads
# ---------------------------------------------------------------------------
def _read_input(path: Path, retries: int = 3, sleep_s: float = 0.1) -> dict:
    """Read + parse JSON. Retries briefly to avoid mid-write races."""
    last_err: Exception | None = None
    for _ in range(retries):
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            last_err = e
            time.sleep(sleep_s)
    raise RuntimeError(f"could not parse {path}: {last_err}")


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> int:
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    log(f"watching:   {INPUT_PATH}")
    log(f"writing:    {OUTPUT_PATH}")
    if not INPUT_PATH.parent.exists():
        log(f"WARN: {INPUT_PATH.parent} does not exist yet — start Stage 2 first.")
    log("waiting for input...  (Ctrl+C to stop)")

    last_mtime: float | None = None

    while True:
        try:
            if not INPUT_PATH.exists():
                time.sleep(POLL_SECONDS)
                continue

            try:
                mtime = INPUT_PATH.stat().st_mtime
            except OSError:
                time.sleep(POLL_SECONDS)
                continue

            if last_mtime is not None and mtime <= last_mtime:
                time.sleep(POLL_SECONDS)
                continue

            last_mtime = mtime
            log(f"input changed (mtime={mtime:.0f}) -> running model")

            try:
                payload = _read_input(INPUT_PATH)
            except Exception as e:
                err = f"failed to read input: {e}"
                log(f"ERROR: {err}")
                _write_atomic(OUTPUT_PATH, _safe_error_prediction(err))
                continue

            try:
                result = predict_ecg(payload)
                _write_atomic(OUTPUT_PATH, result)
                log(f"prediction written:  label={result['label']}  "
                    f"conf={result['confidence']:.2f}  "
                    f"hr={result.get('heart_rate')}")
            except Exception as e:
                err = f"inference failed: {e}"
                log(f"ERROR: {err}")
                traceback.print_exc(limit=3)
                _write_atomic(OUTPUT_PATH, _safe_error_prediction(err))

        except KeyboardInterrupt:
            log("stopped by user")
            return 0
        except Exception as e:
            log(f"loop error: {e}")
            traceback.print_exc(limit=3)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
