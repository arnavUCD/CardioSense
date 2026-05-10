"""
pipeline/filter.py
Steps 1-5 of the Stage 2 cleaning pipeline.
All filters use filtfilt (zero-phase) so there is no time shift —
critical for accurate R-peak alignment.
"""

import numpy as np
from scipy.signal import butter, filtfilt, iirnotch


def remove_dc(signal: np.ndarray) -> np.ndarray:
    """Step 1 — subtract mean to center signal at zero."""
    return signal - np.mean(signal)


def butterworth_bandpass(
    signal: np.ndarray,
    lowcut: float = 1.0,
    highcut: float = 30.0,
    sample_rate: int = 250,
    order: int = 4,
) -> np.ndarray:
    """
    Step 2 — 4th order Butterworth bandpass.
    1.0 Hz highpass  : removes baseline wander from breathing
    30.0 Hz lowpass  : removes EMG noise and high-freq jitter
    filtfilt         : zero-phase, no time shift
    """
    nyq = sample_rate / 2.0
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, signal)


def notch_filter(
    signal: np.ndarray,
    freq: float = 60.0,
    quality: float = 30.0,
    sample_rate: int = 250,
) -> np.ndarray:
    """
    Step 3 — 60 Hz notch filter for powerline interference.
    Quality factor 30 gives a narrow notch that kills 60 Hz
    without disturbing nearby frequencies.
    """
    nyq = sample_rate / 2.0
    w0 = freq / nyq
    b, a = iirnotch(w0, quality)
    return filtfilt(b, a, signal)


def remove_baseline_wander(
    signal: np.ndarray,
    sample_rate: int = 250,
    window_ms: float = 600.0,
) -> np.ndarray:
    """
    Step 4 — subtract a heavily smoothed version of the signal
    to remove residual slow drift that survived the highpass.
    600ms window aggressively captures breathing-frequency baseline.
    """
    win = int(window_ms / 1000.0 * sample_rate)
    if win % 2 == 0:
        win += 1
    kernel = np.ones(win) / win
    baseline = np.convolve(signal, kernel, mode="same")
    return signal - baseline


def normalize(signal: np.ndarray, clip: float = 4.0) -> np.ndarray:
    """
    Step 5 — z-score normalize then clip.
    Neural network always sees consistent amplitude regardless
    of electrode contact quality or patient body size.
    """
    std = signal.std()
    if std < 1e-8:
        return signal
    normalized = (signal - signal.mean()) / std
    return np.clip(normalized, -clip, clip)


def clean_signal(
    raw: np.ndarray,
    sample_rate: int = 250,
) -> np.ndarray:
    """
    Full cleaning chain — Steps 1 through 5 in order.
    Input  : raw noisy ECG samples (any amplitude)
    Output : cleaned, normalized ECG ready for Pan-Tompkins + model

    Parameters tuned for synthetic hardware-level noise:
    - 1.0-30.0 Hz bandpass (tighter than clinical to handle high noise floor)
    - 600ms baseline wander window (aggressive drift removal)
    """
    s = remove_dc(raw)
    s = butterworth_bandpass(s, lowcut=1.0, highcut=30.0, sample_rate=sample_rate, order=4)
    s = notch_filter(s, sample_rate=sample_rate)
    s = remove_baseline_wander(s, sample_rate=sample_rate, window_ms=600.0)
    s = normalize(s)
    return s
