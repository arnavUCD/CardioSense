"""
pipeline/hrv.py
Step 7-8: RR interval validation and HRV feature extraction.
These features feed directly into the neural network's feature branch.
"""

import numpy as np


def compute_rr_intervals(
    r_peaks: list[int],
    sample_rate: int = 250,
) -> list[float]:
    """
    Convert R-peak sample indices to RR intervals in milliseconds.
    """
    if len(r_peaks) < 2:
        return []
    rr = np.diff(r_peaks) / sample_rate * 1000.0
    return rr.tolist()


def validate_rr_intervals(
    rr_intervals: list[float],
    min_rr_ms: float = 300.0,   # > 200 bpm — physiologically impossible
    max_rr_ms: float = 2000.0,  # < 30 bpm  — likely missed beat
) -> tuple[list[float], str]:
    """
    Discard physiologically impossible RR intervals.
    Returns (valid_rr_list, quality_flag).
    """
    if not rr_intervals:
        return [], "low"

    rr = np.array(rr_intervals)
    valid = rr[(rr >= min_rr_ms) & (rr <= max_rr_ms)]

    n_total = len(rr)
    n_valid = len(valid)

    if n_valid == 0:
        quality = "low"
    elif n_valid < 3:
        quality = "low"
    elif n_valid / n_total < 0.7:
        quality = "noisy"
    else:
        quality = "good"

    return valid.tolist(), quality


def extract_hrv_features(rr_intervals: list[float]) -> dict:
    """
    Compute all HRV features from validated RR intervals.
    These are the features fed to the neural network feature branch.

    Returns dict with:
      mean_rr  : mean RR interval (ms)
      sdnn     : std dev of RR intervals — overall variability
      rmssd    : root mean square of successive differences — short-term variability
      pnn50    : % of successive differences > 50ms
      cv       : coefficient of variation (sdnn / mean_rr) — normalised variability
      mean_hr  : mean heart rate (bpm)
    """
    if len(rr_intervals) < 2:
        return {
            "mean_rr": 0.0,
            "sdnn": 0.0,
            "rmssd": 0.0,
            "pnn50": 0.0,
            "cv": 0.0,
            "mean_hr": 0.0,
        }

    rr = np.array(rr_intervals)

    mean_rr = float(np.mean(rr))
    sdnn    = float(np.std(rr, ddof=1)) if len(rr) > 1 else 0.0

    # Successive differences
    diff_rr = np.diff(rr)
    rmssd   = float(np.sqrt(np.mean(diff_rr ** 2))) if len(diff_rr) > 0 else 0.0
    pnn50   = float(np.mean(np.abs(diff_rr) > 50.0) * 100.0) if len(diff_rr) > 0 else 0.0

    cv      = float(sdnn / mean_rr) if mean_rr > 0 else 0.0
    mean_hr = float(60000.0 / mean_rr) if mean_rr > 0 else 0.0

    return {
        "mean_rr": round(mean_rr, 2),
        "sdnn":    round(sdnn, 2),
        "rmssd":   round(rmssd, 2),
        "pnn50":   round(pnn50, 2),
        "cv":      round(cv, 4),
        "mean_hr": round(mean_hr, 1),
    }
