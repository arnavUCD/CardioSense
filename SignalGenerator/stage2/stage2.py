"""
stage2.py
Reads latest_result.json every 3s → cleans signal → writes model_input.json

Output fully satisfies CardioSense ML Layer Input Contract (Mode A + B).

Run with:
    python3 stage2.py
"""

import json
import time
import os
import numpy as np
from datetime import datetime, timezone

from pipeline.filter import clean_signal
from pipeline.peaks  import detect_r_peaks
from pipeline.hrv    import compute_rr_intervals, validate_rr_intervals, extract_hrv_features

BASE        = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(BASE, '..', 'stage1', 'latest_result.json')
OUTPUT_FILE = os.path.join(BASE, "shared", "input.json")
SAMPLE_RATE = 250
INTERVAL_S  = 3.0
PATIENT_ID  = "demo-patient-01"   # swap for real patient ID in production


def sanitize(raw: np.ndarray) -> np.ndarray:
    """
    Replace NaN / Inf with last good value (forward fill).
    His contract: No NaN, no null inside the array.
    """
    arr = raw.copy()
    for i in range(len(arr)):
        if not np.isfinite(arr[i]):
            arr[i] = arr[i - 1] if i > 0 else 0.0
    return arr


def process_window(raw_ecg: list, sample_rate: int = SAMPLE_RATE) -> dict:
    raw     = sanitize(np.array(raw_ecg, dtype=float))
    cleaned = clean_signal(raw, sample_rate=sample_rate)
    r_peaks = detect_r_peaks(cleaned, sample_rate=sample_rate)
    rr_raw  = compute_rr_intervals(r_peaks, sample_rate)
    rr_valid, quality = validate_rr_intervals(rr_raw)
    hrv     = extract_hrv_features(rr_valid)

    # ── CardioSense contract fields ───────────────────────────────────────────
    return {
        # Required
        "clean_ecg":    cleaned.tolist(),       # 2500 floats, 1D, no NaN
        "sample_rate":  sample_rate,            # 250

        # Strongly recommended
        "r_peaks":      r_peaks,                # sample indices
        "rr_intervals": rr_valid,               # ms, optional but we have it

        # Pass-through (ignored by model, useful for frontend)
        "patient_id":   PATIENT_ID,
        "timestamp":    datetime.now(timezone.utc).timestamp(),

        # Our extras — harmless passthrough per contract
        "quality":      quality,
        "hrv_features": hrv,
        "window_info":  {
            "n_beats":    len(r_peaks),
            "duration_s": round(len(raw) / sample_rate, 1),
            "stride_s":   INTERVAL_S,
        },
    }


def run():
    print("[Stage 2] Started — CardioSense input contract v1")
    print(f"[Stage 2] Input  → {INPUT_FILE}")
    print(f"[Stage 2] Output → {OUTPUT_FILE}")
    print(f"[Stage 2] Patient: {PATIENT_ID}")
    print()

    last_mtime = None

    while True:
        try:
            if not os.path.exists(INPUT_FILE):
                print("[Stage 2] Waiting for Stage 1...")
                time.sleep(1)
                continue

            mtime = os.path.getmtime(INPUT_FILE)
            if mtime == last_mtime:
                time.sleep(0.5)
                continue

            with open(INPUT_FILE) as f:
                stage1 = json.load(f)

            raw_ecg        = stage1.get("clean_ecg", [])
            sample_rate    = stage1.get("sample_rate", SAMPLE_RATE)
            rhythm_mode    = stage1.get("rhythm_mode", "normal")
            classification = stage1.get("classification", "Unknown")

            if len(raw_ecg) < 500:
                time.sleep(0.5)
                continue

            result = process_window(raw_ecg, sample_rate=sample_rate)

            # Metadata passthrough
            result["rhythm_mode"]    = rhythm_mode
            result["classification"] = classification

            with open(OUTPUT_FILE, "w") as f:
                json.dump(result, f)

            last_mtime = mtime

            hrv = result["hrv_features"]
            print(
                f"[Stage 2] {rhythm_mode:6s} | "
                f"beats={result['window_info']['n_beats']:2d} | "
                f"HR={hrv['mean_hr']:5.1f} bpm | "
                f"SDNN={hrv['sdnn']:6.1f} ms | "
                f"RMSSD={hrv['rmssd']:6.1f} ms | "
                f"pNN50={hrv['pnn50']:5.1f}% | "
                f"quality={result['quality']}"
            )

        except json.JSONDecodeError:
            time.sleep(0.2)
        except Exception as e:
            print(f"[Stage 2] Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    run()
