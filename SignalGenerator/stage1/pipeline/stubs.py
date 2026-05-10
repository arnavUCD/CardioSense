"""
pipeline/stubs.py — Phase 1 stubs.
Uses a smoothed envelope for peak detection to avoid noise false positives.
"""

import os
import numpy as np
from pipeline.contract import ECGWindow, InferenceResult

BASE      = os.path.dirname(os.path.dirname(__file__))
MODE_FILE = os.path.join(BASE, "mode.txt")


def read_rhythm():
    try:
        with open(MODE_FILE) as f:
            val = f.read().strip()
            return val if val in ("normal", "afib") else "normal"
    except Exception:
        return "normal"


def simple_peak_detect(signal: np.ndarray, sample_rate: int = 250) -> list[int]:
    """
    Smoothed envelope peak detector.
    Squares + moving average to suppress noise before thresholding.
    """
    # Square to emphasise large deflections
    squared = signal ** 2

    # Moving average over 150ms window to smooth out noise spikes
    win = int(0.15 * sample_rate)
    kernel = np.ones(win) / win
    smoothed = np.convolve(squared, kernel, mode='same')

    threshold = smoothed.mean() + 0.8 * smoothed.std()
    refractory = int(0.35 * sample_rate)  # 350ms — no two beats closer than this

    peaks = []
    i = 0
    while i < len(smoothed):
        if smoothed[i] > threshold:
            end = min(i + refractory, len(smoothed))
            local_max = i + int(np.argmax(smoothed[i:end]))
            peaks.append(local_max)
            i = local_max + refractory
        else:
            i += 1

    return peaks


def stub_clean(raw_samples: list[float], sample_rate: int = 250) -> ECGWindow:
    signal = np.array(raw_samples, dtype=float)

    if signal.std() > 0:
        signal = (signal - signal.mean()) / signal.std()
        signal = np.clip(signal, -3, 3)

    r_peaks = simple_peak_detect(signal, sample_rate)

    rr_intervals = (np.diff(r_peaks) / sample_rate * 1000).tolist() if len(r_peaks) > 1 else []

    return ECGWindow(
        clean_ecg=signal.tolist(),
        r_peaks=r_peaks,
        rr_intervals=rr_intervals,
        sample_rate=sample_rate,
        quality="good",
    )


def stub_infer(window: ECGWindow) -> InferenceResult:
    rhythm = read_rhythm()

    rr     = np.array(window.rr_intervals) if window.rr_intervals else np.array([833.0])
    bpm    = round(float(60000.0 / rr.mean()), 1) if len(rr) > 0 else 72.0
    rr_std = round(float(rr.std()), 1) if len(rr) > 1 else 0.0

    # Override with realistic values — noisy signal ruins raw peak detection
    if rhythm == "afib":
        rr_std = round(float(np.random.uniform(110, 160)), 1)
    else:
        rr_std = round(float(np.random.uniform(8, 18)), 1)

    if rhythm == "afib":
        classification = "AFib"
        probs          = {"Normal": 0.04, "AFib": 0.91, "Other": 0.05}
        confidence     = 0.91
    else:
        classification = "Normal"
        probs          = {"Normal": 0.92, "AFib": 0.05, "Other": 0.03}
        confidence     = 0.92

    return InferenceResult(
        classification=classification,
        confidence=confidence,
        probabilities=probs,
        bpm=bpm,
        rr_std=rr_std,
        quality=window.quality,
        clean_ecg=window.clean_ecg,
        r_peaks=window.r_peaks,
    )
