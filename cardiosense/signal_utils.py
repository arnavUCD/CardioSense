"""Signal-processing helpers: filtering, R-peak detection, HRV metrics."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, resample_poly

from .config import TARGET_FS


def bandpass_filter(signal: np.ndarray, fs: int = TARGET_FS,
                    low: float = 0.5, high: float = 40.0,
                    order: int = 3) -> np.ndarray:
    """Zero-phase bandpass to remove baseline wander and high-frequency noise."""
    nyq = fs / 2.0
    high = min(high, nyq * 0.99)
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, signal).astype(np.float32)


def zscore(window: np.ndarray) -> np.ndarray:
    """Per-window z-score normalisation."""
    mu = float(window.mean())
    sd = float(window.std())
    if sd < 1e-6:
        return np.zeros_like(window, dtype=np.float32)
    return ((window - mu) / sd).astype(np.float32)


def resample_to_target(signal: np.ndarray, fs: int,
                       target_fs: int = TARGET_FS) -> np.ndarray:
    """Resample arbitrary-rate ECG to the model's TARGET_FS."""
    if fs == target_fs:
        return signal.astype(np.float32)
    from math import gcd
    g = gcd(int(fs), int(target_fs))
    up = int(target_fs // g)
    down = int(fs // g)
    return resample_poly(signal, up, down).astype(np.float32)


def detect_r_peaks(signal: np.ndarray, fs: int = TARGET_FS) -> np.ndarray:
    """
    Lightweight Pan-Tompkins-style R-peak detector.
    Differentiate -> square -> moving-average integrate -> peak-pick.
    Returns sample indices of detected R-peaks.
    """
    if len(signal) < fs:
        return np.array([], dtype=int)

    filt = bandpass_filter(signal, fs=fs, low=5.0, high=15.0, order=2)
    diff = np.diff(filt, prepend=filt[0])
    sq = diff ** 2
    win = max(1, int(0.15 * fs))
    integ = np.convolve(sq, np.ones(win) / win, mode="same")

    # Adaptive threshold: peaks must clear 35% of a robust max.
    thr = 0.35 * np.percentile(integ, 99.5)
    if thr <= 0:
        return np.array([], dtype=int)

    # Refractory period ~ 200 ms (max ~300 bpm).
    distance = int(0.2 * fs)
    peaks, _ = find_peaks(integ, height=thr, distance=distance)

    # Snap each detection to the local max of the band-passed signal nearby.
    half = int(0.05 * fs)
    refined = []
    for p in peaks:
        a = max(0, p - half)
        b = min(len(filt), p + half + 1)
        refined.append(a + int(np.argmax(filt[a:b])))
    return np.array(sorted(set(refined)), dtype=int)


def hrv_stats(rr_ms: np.ndarray) -> dict:
    """Compute standard HRV stats from RR intervals (in ms)."""
    rr_ms = np.asarray(rr_ms, dtype=float)
    rr_ms = rr_ms[(rr_ms > 250) & (rr_ms < 2000)]  # physiologic plausibility
    if rr_ms.size < 2:
        return {
            "rmssd": None,
            "sdnn": None,
            "pnn50": None,
            "mean_rr_ms": None,
        }
    diffs = np.diff(rr_ms)
    rmssd = float(np.sqrt(np.mean(diffs ** 2)))
    sdnn = float(rr_ms.std(ddof=1)) if rr_ms.size > 1 else 0.0
    pnn50 = float(np.mean(np.abs(diffs) > 50.0))
    mean_rr = float(rr_ms.mean())
    return {
        "rmssd": round(rmssd, 2),
        "sdnn": round(sdnn, 2),
        "pnn50": round(pnn50, 4),
        "mean_rr_ms": round(mean_rr, 2),
    }


def heart_rate_bpm(rr_ms: np.ndarray) -> float | None:
    rr_ms = np.asarray(rr_ms, dtype=float)
    rr_ms = rr_ms[(rr_ms > 250) & (rr_ms < 2000)]
    if rr_ms.size == 0:
        return None
    return round(60_000.0 / rr_ms.mean(), 1)


def rr_intervals_ms(r_peaks: np.ndarray, fs: int = TARGET_FS) -> np.ndarray:
    if len(r_peaks) < 2:
        return np.array([], dtype=float)
    return np.diff(r_peaks).astype(float) * (1000.0 / fs)
