"""Build training data from the MIT-BIH AFib + Arrhythmia databases.

Both databases produce labelled fixed-length windows the model trains on:

* AFib DB: 250 Hz, ECG1 column, rhythm changes via aux_note like "(N", "(AFIB".
* Arrhythmia DB: 360 Hz, MLII (or first non-V) column, aux_notes like "(N0".

For each record we
  1. Load the chosen ECG channel.
  2. Resample to TARGET_FS if needed.
  3. Build (start, end, label) intervals from rhythm-change annotations,
     skipping paced / artifact / unknown rhythms.
  4. Tile each interval into non-overlapping WINDOW_SAMPLES windows.
  5. Bandpass-filter and z-score each window.

Splits are at the *record* level so a held-out record never has any
window in the training set.
"""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from .config import (
    AFIB_DIR,
    AFIB_FS,
    ARRHYTHMIA_DIR,
    ARRHYTHMIA_FS,
    MAX_WINDOWS_PER_RECORD_PER_CLASS,
    RHYTHM_TO_LABEL,
    SKIP_RHYTHMS,
    TARGET_FS,
    WINDOW_SAMPLES,
)
from .signal_utils import bandpass_filter, resample_to_target, zscore


@dataclass
class RhythmInterval:
    start: int          # sample index at TARGET_FS, inclusive
    end: int            # sample index at TARGET_FS, exclusive
    label: int          # 0 = Normal, 1 = Arrhythmia


# ---------------------------------------------------------------------------
# Database-specific loaders
# ---------------------------------------------------------------------------

# Annotation symbols that mark events (not actual heartbeats).
# Anything else in `symbol` is a per-beat label.
_NON_BEAT_SYMBOLS = {"+", "~", "|", '"', "*", "=", "@", "s", "T"}


def _load_afib(record: str) -> tuple[np.ndarray, list[tuple[int, str]],
                                     list[tuple[int, str]] | None, int]:
    """Return (signal, rhythm_markers, beats_or_None, native_fs)."""
    df = pd.read_csv(AFIB_DIR / f"{record}_ekg.csv", usecols=["ECG1"])
    sig = df["ECG1"].to_numpy(dtype=np.float32)

    ann = json.loads((AFIB_DIR / f"{record}_annotations.json").read_text())
    samples = ast.literal_eval(ann["sample"])
    notes = ann["aux_note"]
    # AFib DB rhythm intervals are macro-clean, no per-beat purity check needed.
    return sig, list(zip(samples, notes)), None, AFIB_FS


def _arrhythmia_ecg_column(df_columns: list[str]) -> str | None:
    """Pick a usable ECG column from an Arrhythmia DB CSV."""
    candidates = [c for c in df_columns if c not in ("Unnamed: 0", "symbol")]
    if not candidates:
        return None
    if "MLII" in candidates:
        return "MLII"
    return candidates[0]


def _load_arrhythmia(record: str) -> tuple[np.ndarray, list[tuple[int, str]],
                                           list[tuple[int, str]], int]:
    """Return (signal, rhythm_markers, beats, native_fs).

    `beats` is the per-beat list `[(sample_idx, beat_symbol), ...]` we use to
    filter Normal windows: ectopic beats (PVCs etc.) are sprinkled inside
    "(N" rhythm intervals, so a beat-purity check keeps Normal training data
    actually normal.
    """
    csv_path = ARRHYTHMIA_DIR / f"{record}_ekg.csv"
    header = pd.read_csv(csv_path, nrows=0)
    col = _arrhythmia_ecg_column(list(header.columns))
    if col is None:
        raise RuntimeError(f"no ECG column found in {csv_path}")
    df = pd.read_csv(csv_path, usecols=[col])
    sig = df[col].to_numpy(dtype=np.float32)

    ann = json.loads((ARRHYTHMIA_DIR / f"{record}_annotations_1.json").read_text())
    samples = ast.literal_eval(ann["sample"])
    syms = ann["symbol"]
    aux_notes = ann.get("aux_note") or [""] * len(samples)

    markers = [(s, a) for s, a in zip(samples, aux_notes) if a]
    beats = [(s, sym) for s, sym in zip(samples, syms)
             if sym not in _NON_BEAT_SYMBOLS]
    return sig, markers, beats, ARRHYTHMIA_FS


# ---------------------------------------------------------------------------
# Generic windowing
# ---------------------------------------------------------------------------

def _intervals_from_markers(markers: list[tuple[int, str]],
                            total_samples_target_fs: int,
                            native_fs: int) -> list[RhythmInterval]:
    """Convert rhythm-change markers (in native fs) into labelled intervals
    (in TARGET_FS sample indices). Skips unknown / paced / artifact rhythms."""
    if not markers:
        return []
    scale = TARGET_FS / float(native_fs)
    intervals: list[RhythmInterval] = []
    for i, (s_native, note) in enumerate(markers):
        if note in SKIP_RHYTHMS:
            continue
        label = RHYTHM_TO_LABEL.get(note)
        if label is None:
            continue
        end_native = (markers[i + 1][0] if i + 1 < len(markers)
                      else int(total_samples_target_fs / scale))
        start = int(round(s_native * scale))
        end = int(round(end_native * scale))
        end = min(end, total_samples_target_fs)
        if end - start >= WINDOW_SAMPLES:
            intervals.append(RhythmInterval(start, end, label))
    return intervals


def _is_pure_normal_window(start: int, end: int,
                           beats_target_fs: np.ndarray | None,
                           beat_syms: list[str] | None) -> bool:
    """A window qualifies as Normal-pure only if every beat inside is 'N'.

    If we have no beat info (AFib DB), trust the rhythm-level annotation.
    """
    if beats_target_fs is None or beat_syms is None:
        return True
    mask = (beats_target_fs >= start) & (beats_target_fs < end)
    syms_in_window = [beat_syms[i] for i, m in enumerate(mask) if m]
    if not syms_in_window:
        return False  # no beats detected -> probably bad signal
    return all(s == "N" for s in syms_in_window)


def _windows_from_signal(signal_target_fs: np.ndarray,
                         intervals: list[RhythmInterval],
                         cap_per_class: int,
                         rng: np.random.Generator,
                         beats_target_fs: np.ndarray | None = None,
                         beat_syms: list[str] | None = None,
                         ) -> tuple[np.ndarray, np.ndarray]:
    """Bandpass + z-score each non-overlapping window inside the intervals.

    When `beats_target_fs` and `beat_syms` are provided, Normal windows
    must contain only 'N' beats to be included (purity filter)."""
    if not intervals:
        return (np.empty((0, WINDOW_SAMPLES), dtype=np.float32),
                np.empty((0,), dtype=np.int64))

    filtered = bandpass_filter(signal_target_fs, fs=TARGET_FS)
    by_label: dict[int, list[np.ndarray]] = {0: [], 1: []}
    for iv in intervals:
        starts = list(range(iv.start, iv.end - WINDOW_SAMPLES + 1, WINDOW_SAMPLES))
        for st in starts:
            w = filtered[st:st + WINDOW_SAMPLES]
            if len(w) != WINDOW_SAMPLES:
                continue
            if np.std(w) < 1e-4:        # discard flat / disconnected windows
                continue
            # Per-beat purity filter for Normal windows only.
            if iv.label == 0 and not _is_pure_normal_window(
                    st, st + WINDOW_SAMPLES, beats_target_fs, beat_syms):
                continue
            by_label[iv.label].append(zscore(w))

    Xs, ys = [], []
    for label, ws in by_label.items():
        if not ws:
            continue
        if len(ws) > cap_per_class:
            idx = rng.choice(len(ws), cap_per_class, replace=False)
            ws = [ws[i] for i in idx]
        Xs.extend(ws)
        ys.extend([label] * len(ws))

    if not Xs:
        return (np.empty((0, WINDOW_SAMPLES), dtype=np.float32),
                np.empty((0,), dtype=np.int64))
    return np.stack(Xs).astype(np.float32), np.array(ys, dtype=np.int64)


def _windows_from_record_generic(record: str,
                                 loader: Callable[[str], tuple[np.ndarray, list, list | None, int]],
                                 cap_per_class: int,
                                 rng: np.random.Generator
                                 ) -> tuple[np.ndarray, np.ndarray]:
    sig, markers, beats, native_fs = loader(record)
    sig_resampled = resample_to_target(sig, fs=native_fs, target_fs=TARGET_FS)
    intervals = _intervals_from_markers(markers, len(sig_resampled), native_fs)
    if beats is not None:
        scale = TARGET_FS / float(native_fs)
        beat_idx = np.array([s for s, _ in beats], dtype=np.int64)
        beat_idx = (beat_idx * scale).astype(np.int64)
        beat_syms = [sym for _, sym in beats]
    else:
        beat_idx = None
        beat_syms = None
    return _windows_from_signal(sig_resampled, intervals, cap_per_class, rng,
                                beats_target_fs=beat_idx, beat_syms=beat_syms)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def list_afib_records(afib_dir: Path = AFIB_DIR) -> list[str]:
    return sorted({p.stem.split("_")[0] for p in afib_dir.glob("*_ekg.csv")})


def list_arrhythmia_records(arr_dir: Path = ARRHYTHMIA_DIR) -> list[str]:
    return sorted({p.stem.split("_")[0] for p in arr_dir.glob("*_ekg.csv")})


def list_records() -> list[tuple[str, str]]:
    """Return all records as (db_name, record_id) tuples."""
    out = [("afib", r) for r in list_afib_records()]
    out += [("arrhythmia", r) for r in list_arrhythmia_records()]
    return out


def windows_from_record(db: str, record: str,
                        cap_per_class: int = MAX_WINDOWS_PER_RECORD_PER_CLASS,
                        rng: np.random.Generator | None = None
                        ) -> tuple[np.ndarray, np.ndarray]:
    rng = rng or np.random.default_rng(0)
    if db == "afib":
        return _windows_from_record_generic(record, _load_afib, cap_per_class, rng)
    if db == "arrhythmia":
        return _windows_from_record_generic(record, _load_arrhythmia, cap_per_class, rng)
    raise ValueError(f"unknown db: {db!r}")


def build_dataset(records: Iterable[tuple[str, str]],
                  cap_per_class: int = MAX_WINDOWS_PER_RECORD_PER_CLASS,
                  seed: int = 0,
                  verbose: bool = True
                  ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build (X, y, rec_id_strings) for a list of (db, record) pairs."""
    rng = np.random.default_rng(seed)
    Xs, ys, recs = [], [], []
    for db, r in records:
        try:
            X, y = windows_from_record(db, r, cap_per_class, rng=rng)
        except Exception as e:
            if verbose:
                print(f"  {db}/{r}: SKIPPED ({e})")
            continue
        if verbose:
            n0 = int((y == 0).sum())
            n1 = int((y == 1).sum())
            print(f"  {db:<11} {r}: Normal={n0:4d}  Arrhythmia={n1:4d}")
        Xs.append(X)
        ys.append(y)
        recs.append(np.full(len(y), f"{db}/{r}", dtype=object))
    if not Xs or sum(len(x) for x in Xs) == 0:
        raise RuntimeError("no data built — check raw/ directory")
    return (np.concatenate(Xs, axis=0),
            np.concatenate(ys, axis=0),
            np.concatenate(recs, axis=0))


def record_split(records: list[tuple[str, str]], seed: int = 0,
                 test_frac: float = 0.20
                 ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Record-level split, stratified roughly by db."""
    rng = np.random.default_rng(seed)
    by_db: dict[str, list[tuple[str, str]]] = {}
    for db, r in records:
        by_db.setdefault(db, []).append((db, r))
    train, test = [], []
    for db, recs in by_db.items():
        recs = sorted(recs)
        rng.shuffle(recs)
        n_test = max(1, int(round(len(recs) * test_frac)))
        test.extend(recs[:n_test])
        train.extend(recs[n_test:])
    return train, test
