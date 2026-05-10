"""Inference module for the CardioSense ML layer.

Public entry point: `predict_ecg(input_data, sample_rate=None)`.

`input_data` may be:
  * a path to a CSV file (auto-detect ECG column)
  * a path to a JSON file
  * a dict with keys like {"clean_ecg", "sample_rate", "r_peaks", "rr_intervals"}
  * a 1D numpy array / Python list of ECG samples
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from .config import (
    CLASSES,
    MODEL_PATH,
    TARGET_FS,
    UNCERTAIN_CONFIDENCE,
    UNCERTAIN_LABEL,
    WINDOW_SAMPLES,
    WINDOW_SECONDS,
)
from .model import ECGCNN
from .signal_utils import (
    bandpass_filter,
    detect_r_peaks,
    heart_rate_bpm,
    hrv_stats,
    resample_to_target,
    rr_intervals_ms,
    zscore,
)

# Common column names produced by various ECG sources.
ECG_COLUMN_CANDIDATES = ("ECG1", "ECG2", "ecg", "ECG", "signal",
                         "value", "voltage", "MLII", "II", "V5")


_model_cache: dict[str, Any] = {}


def _load_model(device: torch.device | None = None) -> tuple[ECGCNN, torch.device]:
    if "model" in _model_cache:
        return _model_cache["model"], _model_cache["device"]
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"trained model not found at {MODEL_PATH}. "
            "Run `python -m cardiosense.train` first."
        )
    device = device or torch.device(
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    model = ECGCNN()
    model.load_state_dict(ckpt["model_state"])
    model.to(device).eval()
    _model_cache["model"] = model
    _model_cache["device"] = device
    return model, device


def _autodetect_ecg_column(df: pd.DataFrame) -> str:
    for c in ECG_COLUMN_CANDIDATES:
        if c in df.columns:
            return c
    # Fall back to the first numeric column that is not an index marker.
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        raise ValueError(f"could not find an ECG column. Columns: {list(df.columns)}")
    return numeric[0]


def _from_csv(path: Path
              ) -> tuple[np.ndarray, int | None, np.ndarray | None, np.ndarray | None]:
    df = pd.read_csv(path)
    col = _autodetect_ecg_column(df)
    return df[col].to_numpy(dtype=np.float32), None, None, None


def _from_json(payload: dict
               ) -> tuple[np.ndarray, int | None, np.ndarray | None, np.ndarray | None]:
    if "clean_ecg" in payload:
        ecg = np.asarray(payload["clean_ecg"], dtype=np.float32)
    elif "ecg" in payload:
        ecg = np.asarray(payload["ecg"], dtype=np.float32)
    elif "signal" in payload:
        ecg = np.asarray(payload["signal"], dtype=np.float32)
    else:
        raise ValueError("JSON input must contain one of: clean_ecg, ecg, signal.")
    fs = payload.get("sample_rate") or payload.get("fs")
    r_peaks = payload.get("r_peaks")
    if r_peaks is not None:
        r_peaks = np.asarray(r_peaks, dtype=int)
    rr_ms = payload.get("rr_intervals")
    if rr_ms is not None:
        rr_ms = np.asarray(rr_ms, dtype=float)
    return ecg, fs, r_peaks, rr_ms


def _coerce_input(input_data: Any
                  ) -> tuple[np.ndarray, int | None, np.ndarray | None, np.ndarray | None]:
    """Return (ecg_array, sample_rate_or_None, r_peaks_or_None, rr_ms_or_None)."""
    if isinstance(input_data, (str, Path)):
        p = Path(input_data)
        if p.suffix.lower() == ".csv":
            return _from_csv(p)
        if p.suffix.lower() == ".json":
            return _from_json(json.loads(p.read_text()))
        raise ValueError(f"unsupported file type: {p.suffix}")
    if isinstance(input_data, dict):
        return _from_json(input_data)
    if isinstance(input_data, (list, tuple, np.ndarray)):
        return np.asarray(input_data, dtype=np.float32), None, None, None
    raise TypeError(f"unsupported input type: {type(input_data)}")


def _windowize(ecg: np.ndarray, stride: int) -> np.ndarray:
    """Slice ECG into overlapping windows of WINDOW_SAMPLES, z-scored."""
    if len(ecg) < WINDOW_SAMPLES:
        # Pad with zeros so that short signals still produce one window.
        pad = np.zeros(WINDOW_SAMPLES - len(ecg), dtype=np.float32)
        ecg = np.concatenate([ecg, pad])
    starts = list(range(0, len(ecg) - WINDOW_SAMPLES + 1, stride))
    if not starts:
        starts = [0]
    return np.stack([zscore(ecg[s:s + WINDOW_SAMPLES]) for s in starts])


def _signal_quality(ecg_filt: np.ndarray, r_peaks: np.ndarray,
                    duration_s: float) -> tuple[bool, list[str]]:
    """Return (is_clean, reasons_for_concern).

    A signal is flagged 'unclean' if any of:
      * dynamic range / std is near-zero (lead disconnected, all-flat input)
      * fewer than ~0.5 R-peaks per second (detector found nothing usable)
      * almost no peaks at all in a long recording
    """
    reasons: list[str] = []
    if float(np.std(ecg_filt)) < 1e-3:
        reasons.append("flat_signal")
    expected_min_peaks = max(2, int(0.5 * duration_s))  # ~30 bpm floor
    if len(r_peaks) < expected_min_peaks:
        reasons.append("no_r_peaks")
    return (len(reasons) == 0, reasons)


def predict_ecg(input_data: Any,
                sample_rate: int | None = None,
                stride_seconds: float = 5.0,
                uncertain_threshold: float = UNCERTAIN_CONFIDENCE) -> dict:
    """
    Run the CardioSense ML layer on a single ECG recording.

    Returns a JSON-friendly dict matching the format the frontend consumes.
    The `label` field can be "Normal", "Arrhythmia", or "Uncertain" — the
    last one is emitted when (a) model confidence is below
    `uncertain_threshold` or (b) the signal-quality checks fail (flat signal
    / no detectable R-peaks). The model's raw verdict is always available
    in `raw_label` and the full softmax distribution in `probabilities`.
    """
    ecg, fs_in, r_peaks_in, rr_ms_in = _coerce_input(input_data)
    fs = int(sample_rate or fs_in or TARGET_FS)

    # Resample (if needed) and filter.
    ecg = resample_to_target(ecg, fs=fs, target_fs=TARGET_FS)
    if r_peaks_in is not None and fs != TARGET_FS:
        r_peaks_in = (r_peaks_in.astype(float) * (TARGET_FS / fs)).astype(int)
    ecg_filt = bandpass_filter(ecg, fs=TARGET_FS)
    duration_s = len(ecg_filt) / TARGET_FS

    # Slice into windows and run the model.
    stride = max(1, int(stride_seconds * TARGET_FS))
    windows = _windowize(ecg_filt, stride=stride)

    model, device = _load_model()
    with torch.no_grad():
        x = torch.from_numpy(windows).to(device)
        logits = model(x)
        probs = torch.softmax(logits, dim=1).cpu().numpy()

    avg_probs = probs.mean(axis=0)
    pred_idx = int(np.argmax(avg_probs))
    raw_label = CLASSES[pred_idx]
    confidence = float(avg_probs[pred_idx])

    # R-peaks: prefer caller-supplied; otherwise detect on the cleaned signal.
    if r_peaks_in is not None and len(r_peaks_in) >= 2:
        r_peaks = r_peaks_in
    else:
        r_peaks = detect_r_peaks(ecg_filt, fs=TARGET_FS)

    # RR intervals: prefer caller-supplied (Stage 2 already validates them
    # against physiological thresholds); otherwise compute from R-peaks.
    if rr_ms_in is not None and len(rr_ms_in) >= 1:
        rr_ms = rr_ms_in
    else:
        rr_ms = rr_intervals_ms(r_peaks, fs=TARGET_FS)
    hr = heart_rate_bpm(rr_ms)
    hrv = hrv_stats(rr_ms)

    # Signal-quality + confidence check -> decide Uncertain
    is_clean, quality_reasons = _signal_quality(ecg_filt, r_peaks, duration_s)
    is_uncertain = (not is_clean) or (confidence < uncertain_threshold)
    final_label = UNCERTAIN_LABEL if is_uncertain else raw_label

    if confidence < uncertain_threshold and "low_confidence" not in quality_reasons:
        quality_reasons.append("low_confidence")

    return {
        "label": final_label,
        "raw_label": raw_label,
        "confidence": round(confidence, 4),
        "probabilities": {
            CLASSES[0]: round(float(avg_probs[0]), 4),
            CLASSES[1]: round(float(avg_probs[1]), 4),
        },
        "arrhythmia_detected": bool(final_label == CLASSES[1]),
        "is_uncertain": bool(is_uncertain),
        "quality": {
            "ok": bool(is_clean and confidence >= uncertain_threshold),
            "reasons": quality_reasons,
        },
        "heart_rate": hr,
        "hrv": hrv,
        "sample_rate": TARGET_FS,
        "window_seconds": WINDOW_SECONDS,
        "n_windows": int(len(windows)),
        "n_r_peaks": int(len(r_peaks)),
    }
