"""
main.py — writes inference results to latest_result.json every 3s.
Reads rhythm mode from mode.txt (written by dashboard sidebar).

Usage:
    python3 main.py
"""

import asyncio
import json
import os
from collections import deque

from pipeline.stubs import stub_clean as clean_window
from pipeline.stubs import stub_infer as run_inference
from simulation.synthetic_generator import generate_noisy_ecg

SAMPLE_RATE   = 250
WINDOW_SIZE   = 2500
STRIDE        = 750
CHUNK_SIZE    = 10
CHUNK_CADENCE = CHUNK_SIZE / SAMPLE_RATE

BASE          = os.path.dirname(__file__)
OUTPUT_FILE   = os.path.join(BASE, "latest_result.json")
MODE_FILE     = os.path.join(BASE, "mode.txt")

buffer = deque(maxlen=WINDOW_SIZE)
samples_since_last_window = 0


def read_rhythm():
    """Read rhythm mode set by dashboard. Defaults to normal."""
    try:
        with open(MODE_FILE) as f:
            val = f.read().strip()
            return val if val in ("normal", "afib") else "normal"
    except Exception:
        return "normal"


async def process_window():
    raw_window = list(buffer)
    ecg_window = clean_window(raw_window, sample_rate=SAMPLE_RATE)
    result = run_inference(ecg_window)
    data = {
        "classification": result.classification,
        "confidence": result.confidence,
        "probabilities": result.probabilities,
        "bpm": result.bpm,
        "rr_std": result.rr_std,
        "quality": result.quality,
        "clean_ecg": result.clean_ecg,
        "r_peaks": result.r_peaks,
        "rr_intervals": ecg_window.rr_intervals,
        "rhythm_mode": read_rhythm(),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f)
    print(
        f"[Pipeline] {result.classification:6s} "
        f"conf={result.confidence:.2f}  "
        f"bpm={result.bpm:.0f}  "
        f"rhythm={read_rhythm()}"
    )


async def simulate_ble_stream():
    global samples_since_last_window
    print(f"[Sim] Starting  rate={SAMPLE_RATE}Hz  watching mode.txt for rhythm")

    current_rhythm = read_rhythm()
    noisy, _, _ = generate_noisy_ecg(duration_s=60.0, heart_rate_bpm=72.0,
                                      sample_rate=SAMPLE_RATE, rhythm=current_rhythm)
    idx = 0

    while True:
        # Check if rhythm changed — regenerate signal if so
        new_rhythm = read_rhythm()
        if new_rhythm != current_rhythm:
            print(f"[Sim] Rhythm switched: {current_rhythm} → {new_rhythm}")
            current_rhythm = new_rhythm
            noisy, _, _ = generate_noisy_ecg(duration_s=60.0, heart_rate_bpm=72.0,
                                              sample_rate=SAMPLE_RATE, rhythm=current_rhythm)
            idx = 0

        # Loop signal when exhausted
        if idx + CHUNK_SIZE >= len(noisy):
            idx = 0

        chunk = noisy[idx:idx + CHUNK_SIZE].tolist()
        idx += CHUNK_SIZE
        buffer.extend(chunk)
        samples_since_last_window += CHUNK_SIZE

        if len(buffer) == WINDOW_SIZE and samples_since_last_window >= STRIDE:
            samples_since_last_window = 0
            await process_window()

        await asyncio.sleep(CHUNK_CADENCE)


if __name__ == "__main__":
    asyncio.run(simulate_ble_stream())
