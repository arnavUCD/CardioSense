"""
pipeline/peaks.py
Full Pan-Tompkins R-peak detection algorithm (1985).
Runs on the CLEANED signal from filter.py.

Steps:
  1. Bandpass 5-15 Hz  (emphasises QRS, suppresses P/T waves)
  2. Differentiate     (captures QRS slope)
  3. Square            (all positive, amplifies large deflections)
  4. Moving window integrate (150ms window, smooths into detectable envelope)
  5. Adaptive dual-threshold with refractory period
"""

import numpy as np
from scipy.signal import butter, filtfilt


def _bandpass_derivative(signal: np.ndarray, sample_rate: int = 250) -> np.ndarray:
    """Step 1 — narrow bandpass for QRS emphasis."""
    nyq = sample_rate / 2.0
    low = 5.0 / nyq
    high = min(15.0 / nyq, 0.99)
    b, a = butter(2, [low, high], btype="band")
    return filtfilt(b, a, signal)


def _differentiate(signal: np.ndarray, sample_rate: int = 250) -> np.ndarray:
    """Step 2 — 5-point derivative operator."""
    h = sample_rate / 8.0
    diff = np.zeros_like(signal)
    for i in range(2, len(signal) - 2):
        diff[i] = (
            -signal[i - 2] - 2 * signal[i - 1]
            + 2 * signal[i + 1] + signal[i + 2]
        ) / h
    return diff


def _square(signal: np.ndarray) -> np.ndarray:
    """Step 3 — pointwise square."""
    return signal ** 2


def _moving_window_integrate(signal: np.ndarray, sample_rate: int = 250) -> np.ndarray:
    """Step 4 — moving window integration over 150ms."""
    win = int(0.15 * sample_rate)
    kernel = np.ones(win) / win
    return np.convolve(signal, kernel, mode="same")


def _find_peaks_adaptive(
    integrated: np.ndarray,
    sample_rate: int = 250,
) -> list[int]:
    """
    Step 5 — adaptive dual-threshold peak finder.

    Pan-Tompkins uses two running thresholds:
      spki  : signal peak estimate (updates on true QRS)
      npki  : noise peak estimate  (updates on noise peaks)
      threshold1 = npki + 0.25 * (spki - npki)
      threshold2 = 0.5 * threshold1  (used for searchback)

    Refractory period of 200ms prevents double-detection.
    """
    refractory = int(0.2 * sample_rate)   # 200ms
    searchback  = int(0.36 * sample_rate)  # 360ms lookback window

    # Initialise thresholds from first 250ms of signal
    init_window = integrated[: int(sample_rate)]
    spki = init_window.max() * 0.25
    npki = init_window.mean() * 0.5

    peaks = []
    i = 0
    last_r = -refractory  # ensure first beat can be detected

    while i < len(integrated) - 1:
        threshold1 = npki + 0.25 * (spki - npki)

        # Find local max in a small neighbourhood
        lo = max(0, i - 1)
        hi = min(len(integrated), i + 2)
        if integrated[i] == integrated[lo:hi].max() and integrated[i] > threshold1:

            if (i - last_r) >= refractory:
                # True QRS candidate
                spki = 0.125 * integrated[i] + 0.875 * spki
                peaks.append(i)
                last_r = i
            else:
                # Within refractory — treat as noise
                npki = 0.125 * integrated[i] + 0.875 * npki
        else:
            npki = 0.125 * integrated[i] + 0.875 * npki

        i += 1

    return peaks


def _map_to_raw_peaks(
    integrated_peaks: list[int],
    cleaned_signal: np.ndarray,
    sample_rate: int = 250,
) -> list[int]:
    """
    Integrated peaks are time-shifted relative to true R-peaks.
    Find the actual R-peak (max of absolute value) in a ±100ms
    window around each integrated peak on the cleaned signal.
    """
    search = int(0.1 * sample_rate)  # ±100ms
    true_peaks = []
    for p in integrated_peaks:
        lo = max(0, p - search)
        hi = min(len(cleaned_signal), p + search)
        window = cleaned_signal[lo:hi]
        local_max = lo + int(np.argmax(np.abs(window)))
        true_peaks.append(local_max)
    return true_peaks


def detect_r_peaks(
    cleaned_signal: np.ndarray,
    sample_rate: int = 250,
) -> list[int]:
    """
    Full Pan-Tompkins pipeline on a cleaned ECG signal.
    Returns a list of sample indices where R-peaks occur.
    """
    bp   = _bandpass_derivative(cleaned_signal, sample_rate)
    diff = _differentiate(bp, sample_rate)
    sq   = _square(diff)
    intg = _moving_window_integrate(sq, sample_rate)
    raw_peaks = _find_peaks_adaptive(intg, sample_rate)
    r_peaks   = _map_to_raw_peaks(raw_peaks, cleaned_signal, sample_rate)

    # Remove duplicates and sort
    r_peaks = sorted(set(r_peaks))

    return r_peaks
