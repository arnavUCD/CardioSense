"""Validate on 100 held-out clips from BOTH databases.

Reports overall accuracy, per-class recall, confusion matrix, per-DB
breakdown, the new Uncertain-state behavior, and a few example outputs.
"""
from __future__ import annotations

import ast
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from cardiosense.config import (
    AFIB_DIR, ARRHYTHMIA_DIR, ARRHYTHMIA_FS, AFIB_FS,
    CLASSES, MODEL_PATH, RHYTHM_TO_LABEL, SKIP_RHYTHMS,
)
from cardiosense.predict import predict_ecg
from cardiosense.data import _arrhythmia_ecg_column, _NON_BEAT_SYMBOLS

CLIP_SECONDS = 15


def _load_record(db: str, rec: str):
    if db == "afib":
        ecg = pd.read_csv(AFIB_DIR / f"{rec}_ekg.csv",
                          usecols=["ECG1"])["ECG1"].to_numpy(np.float32)
        ann = json.loads((AFIB_DIR / f"{rec}_annotations.json").read_text())
        samples = ast.literal_eval(ann["sample"])
        notes = ann["aux_note"]
        markers = list(zip(samples, notes))
        beats = None
        return ecg, markers, beats, AFIB_FS
    else:  # arrhythmia
        csv_path = ARRHYTHMIA_DIR / f"{rec}_ekg.csv"
        header = pd.read_csv(csv_path, nrows=0)
        col = _arrhythmia_ecg_column(list(header.columns))
        ecg = pd.read_csv(csv_path, usecols=[col])[col].to_numpy(np.float32)
        ann = json.loads((ARRHYTHMIA_DIR / f"{rec}_annotations_1.json").read_text())
        samples = ast.literal_eval(ann["sample"])
        syms = ann["symbol"]
        aux_notes = ann.get("aux_note") or [""] * len(samples)
        markers = [(s, a) for s, a in zip(samples, aux_notes) if a]
        beats = [(s, sym) for s, sym in zip(samples, syms)
                 if sym not in _NON_BEAT_SYMBOLS]
        return ecg, markers, beats, ARRHYTHMIA_FS


def all_clips(db: str, rec: str, seconds: int = CLIP_SECONDS):
    ecg, markers, beats, fs = _load_record(db, rec)
    clip_len = seconds * fs
    out = []
    if not markers:
        return out
    for i, (s, n) in enumerate(markers):
        if n in SKIP_RHYTHMS or n not in RHYTHM_TO_LABEL:
            continue
        end = markers[i + 1][0] if i + 1 < len(markers) else len(ecg)
        if end - s < clip_len + 500:
            continue
        label = CLASSES[RHYTHM_TO_LABEL[n]]
        # For Normal in Arrhythmia DB, only keep clips where all beats are 'N'
        for start in range(s + 500, end - clip_len, clip_len):
            if label == "Normal" and beats is not None:
                in_window = [(bs, sym) for bs, sym in beats
                             if start <= bs < start + clip_len]
                if not in_window or any(sym != "N" for _, sym in in_window):
                    continue
            out.append((db, rec, ecg[start:start + clip_len], label, fs))
    return out


def main():
    metrics = json.loads(MODEL_PATH.with_suffix(".pt").parent
                         .joinpath("metrics.json").read_text())
    test_records = [tuple(s.split("/", 1)) for s in metrics["test_records"]]
    print(f"Held-out records: {len(test_records)}")
    for db, r in test_records:
        print(f"  {db}/{r}")
    print()

    pool = []
    for db, r in test_records:
        pool.extend(all_clips(db, r))
    print(f"Candidate clips: {len(pool)}")
    rng = np.random.default_rng(42)

    # Stratify so we get an even split across (db, class).
    sampled = []
    for db in sorted({c[0] for c in pool}):
        for cls in CLASSES:
            sub = [c for c in pool if c[0] == db and c[3] == cls]
            n_take = min(25, len(sub))
            if n_take == 0:
                continue
            idx = rng.choice(len(sub), n_take, replace=False)
            sampled.extend(sub[i] for i in idx)
            print(f"  {db:<11} {cls:<11}  available={len(sub):>5}  sampling={n_take}")
    rng.shuffle(sampled)
    print(f"\nSelected {len(sampled)} clips total\n")

    print("Running predictions...")
    t0 = time.time()
    results = []
    for db, rec, clip, expected, fs in sampled:
        out = predict_ecg(clip, sample_rate=fs)
        results.append({
            "db": db, "rec": rec, "expected": expected,
            "predicted": out["label"], "raw": out["raw_label"],
            "confidence": out["confidence"],
            "uncertain": out["is_uncertain"],
            "quality_reasons": ", ".join(out["quality"]["reasons"]) or "ok",
            "hr": out["heart_rate"], "rmssd": out["hrv"]["rmssd"],
            "ok_strict": out["label"] == expected,
            "ok_raw": out["raw_label"] == expected,
        })
    print(f"  done in {time.time()-t0:.1f}s\n")

    df = pd.DataFrame(results)
    total = len(df)
    print("=" * 72)
    print(f"OVERALL  (strict — Uncertain counts as wrong):")
    print(f"  {df['ok_strict'].sum()}/{total} correct  ({100*df['ok_strict'].mean():.1f}%)")
    print(f"OVERALL  (raw model verdict, ignoring Uncertain gate):")
    print(f"  {df['ok_raw'].sum()}/{total} correct  ({100*df['ok_raw'].mean():.1f}%)")
    print("=" * 72)
    print()

    print("PER-CLASS (raw model verdict):")
    for cls in CLASSES:
        sub = df[df["expected"] == cls]
        if len(sub) == 0: continue
        n_correct = sub["ok_raw"].sum()
        print(f"  {cls:<12} {n_correct:>3}/{len(sub):<3}  recall = {n_correct/len(sub):.3f}")
    print()

    print("CONFUSION MATRIX (raw verdict):")
    print(f"                       predicted")
    print(f"                    Normal    Arrhythmia")
    for cls in CLASSES:
        row = []
        for pcls in CLASSES:
            n = ((df["expected"] == cls) & (df["raw"] == pcls)).sum()
            row.append(f"{n:>6}")
        print(f"  actual {cls:<10} {row[0]}      {row[1]}")
    print()

    print("UNCERTAIN STATE:")
    n_uncertain = df["uncertain"].sum()
    print(f"  {n_uncertain}/{total} clips flagged Uncertain")
    if n_uncertain > 0:
        for _, r in df[df["uncertain"]].iterrows():
            ok = "OK" if r["ok_raw"] else "WRONG"
            print(f"    {r['db']}/{r['rec']}  expected={r['expected']:<11}  "
                  f"raw={r['raw']:<11}  conf={r['confidence']:.2f}  "
                  f"reasons={r['quality_reasons']}  [{ok} underneath]")
    print()

    print("PER-DB BREAKDOWN:")
    for db in sorted(df["db"].unique()):
        sub = df[df["db"] == db]
        n_correct = sub["ok_raw"].sum()
        print(f"  {db:<11} {n_correct:>3}/{len(sub):<3}  ({100*n_correct/len(sub):.1f}%)")
    print()

    wrong = df[~df["ok_raw"]]
    if len(wrong) > 0:
        print(f"ALL {len(wrong)} INCORRECT (raw verdict):")
        print("  db          rec     expected     raw          conf   uncertain?  reasons")
        print("  " + "-" * 78)
        for _, r in wrong.iterrows():
            unc = "YES" if r["uncertain"] else "no "
            print(f"  {r['db']:<11} {r['rec']:<6}  {r['expected']:<11}  {r['raw']:<11}  "
                  f"{r['confidence']:.2f}   {unc}        {r['quality_reasons']}")


if __name__ == "__main__":
    main()
