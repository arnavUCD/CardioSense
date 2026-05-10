"""Pull labelled clips from held-out records and check predictions."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd

from cardiosense.config import AFIB_DIR, MODEL_PATH, RHYTHM_TO_LABEL, CLASSES
from cardiosense.predict import predict_ecg

CLIP_SECONDS = 30
ROW = "  {idx:>2}  {rec}  {expected:<10}  -> {pred:<10}  conf={conf:.2f}  HR={hr}  {ok}"


def load_record(rec: str):
    ecg = pd.read_csv(AFIB_DIR / f"{rec}_ekg.csv",
                      usecols=["ECG1"])["ECG1"].to_numpy(np.float32)
    ann = json.loads((AFIB_DIR / f"{rec}_annotations.json").read_text())
    samples = ast.literal_eval(ann["sample"])
    notes = ann["aux_note"]
    fs = ann["fs"]
    return ecg, samples, notes, fs


def collect_clips(rec: str, n_per_label: int = 2):
    """Return list of (clip, expected_label_str, fs)."""
    ecg, samples, notes, fs = load_record(rec)
    out = []
    counts = {0: 0, 1: 0}
    for i, (s, n) in enumerate(zip(samples, notes)):
        if n not in RHYTHM_TO_LABEL:
            continue
        end = samples[i + 1] if i + 1 < len(samples) else len(ecg)
        if end - s < CLIP_SECONDS * fs + 2000:
            continue
        lbl = RHYTHM_TO_LABEL[n]
        if counts[lbl] >= n_per_label:
            continue
        # take a clip 1000 samples in to avoid the rhythm transition edge
        start = s + 1000
        clip = ecg[start:start + CLIP_SECONDS * fs]
        out.append((clip, CLASSES[lbl], fs))
        counts[lbl] += 1
        if counts[0] >= n_per_label and counts[1] >= n_per_label:
            break
    return out


def main():
    if not MODEL_PATH.exists():
        raise SystemExit("Train first: python -m cardiosense.train")
    metrics = json.loads((MODEL_PATH.parent / "metrics.json").read_text())
    test_records = metrics["test_records"]
    print(f"Held-out records: {test_records}\n")

    rows = []
    for rec in test_records:
        for clip, expected, fs in collect_clips(rec, n_per_label=2):
            out = predict_ecg(clip, sample_rate=fs)
            rows.append({
                "rec": rec,
                "expected": expected,
                "pred": out["label"],
                "conf": out["confidence"],
                "hr": out["heart_rate"],
                "ok": out["label"] == expected,
            })

    print(f"{'idx':>3}  rec     expected    -> predicted    conf   HR    result")
    print("  " + "-" * 64)
    correct = 0
    for i, r in enumerate(rows, 1):
        ok = "OK" if r["ok"] else "WRONG"
        correct += int(r["ok"])
        print(ROW.format(idx=i, rec=r["rec"], expected=r["expected"],
                         pred=r["pred"], conf=r["conf"], hr=r["hr"], ok=ok))

    print("  " + "-" * 64)
    print(f"  {correct}/{len(rows)} correct ({100 * correct / len(rows):.1f}%)")

    print("\nPer-class confidence distribution:")
    for cls in CLASSES:
        confs = [r["conf"] for r in rows if r["expected"] == cls and r["ok"]]
        wrong = [r["conf"] for r in rows if r["expected"] == cls and not r["ok"]]
        print(f"  {cls:<10}  correct mean conf: "
              f"{np.mean(confs) if confs else float('nan'):.3f} (n={len(confs)})  "
              f"wrong: n={len(wrong)}")


if __name__ == "__main__":
    main()
