"""Train the CardioSense binary classifier on MIT-BIH AFib records."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)
from torch.utils.data import DataLoader, TensorDataset

from .config import (
    ARTIFACTS_DIR,
    CLASSES,
    METRICS_PATH,
    MODEL_PATH,
    WINDOW_SAMPLES,
)
from .data import build_dataset, list_records, record_split
from .model import ECGCNN, count_parameters


@dataclass
class TrainConfig:
    epochs: int = 12
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-4
    seed: int = 42
    test_frac: float = 0.25


def _to_loader(X: np.ndarray, y: np.ndarray, batch_size: int,
               shuffle: bool) -> DataLoader:
    ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, drop_last=False)


def _class_weights(y: np.ndarray) -> torch.Tensor:
    counts = np.bincount(y, minlength=len(CLASSES)).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    inv = counts.sum() / (len(CLASSES) * counts)
    return torch.tensor(inv, dtype=torch.float32)


def _evaluate(model: nn.Module, loader: DataLoader, device: torch.device
              ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    ys, preds, probs = [], [], []
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device)
            logits = model(xb)
            p = torch.softmax(logits, dim=1).cpu().numpy()
            preds.append(p.argmax(axis=1))
            probs.append(p)
            ys.append(yb.numpy())
    return (np.concatenate(ys), np.concatenate(preds), np.concatenate(probs))


def train(cfg: TrainConfig | None = None) -> dict:
    cfg = cfg or TrainConfig()
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Listing records ...")
    records = list_records()
    n_afib = sum(1 for db, _ in records if db == "afib")
    n_arr = sum(1 for db, _ in records if db == "arrhythmia")
    print(f"      {len(records)} total records ({n_afib} AFib + {n_arr} Arrhythmia)")
    train_recs, test_recs = record_split(records, seed=cfg.seed,
                                         test_frac=cfg.test_frac)
    fmt = lambda lst: ", ".join(f"{db}/{r}" for db, r in lst)
    print(f"      train records ({len(train_recs)}): {fmt(train_recs)}")
    print(f"      test  records ({len(test_recs)}): {fmt(test_recs)}")

    print("\n[2/4] Building windows ...")
    t0 = time.time()
    X_train, y_train, _ = build_dataset(train_recs, seed=cfg.seed)
    X_test, y_test, rec_test = build_dataset(test_recs, seed=cfg.seed + 1)
    print(f"      train: X={X_train.shape}  y_dist={np.bincount(y_train).tolist()}")
    print(f"      test:  X={X_test.shape}   y_dist={np.bincount(y_test).tolist()}")
    print(f"      build time: {time.time() - t0:.1f}s")

    device = torch.device("cuda" if torch.cuda.is_available()
                          else "mps" if torch.backends.mps.is_available()
                          else "cpu")
    print(f"\n[3/4] Training on device={device}")

    model = ECGCNN().to(device)
    print(f"      params: {count_parameters(model):,}")

    train_loader = _to_loader(X_train, y_train, cfg.batch_size, shuffle=True)
    test_loader = _to_loader(X_test, y_test, cfg.batch_size, shuffle=False)

    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr,
                           weight_decay=cfg.weight_decay)
    loss_fn = nn.CrossEntropyLoss(weight=_class_weights(y_train).to(device))

    best_f1 = -1.0
    best_state = None
    history = []
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        epoch_loss = 0.0
        n = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            epoch_loss += loss.item() * xb.size(0)
            n += xb.size(0)
        epoch_loss /= max(n, 1)

        y_true, y_pred, _ = _evaluate(model, test_loader, device)
        macro_f1 = f1_score(y_true, y_pred, average="macro")
        rec_per_class = recall_score(y_true, y_pred, average=None,
                                     labels=list(range(len(CLASSES))))
        history.append({
            "epoch": epoch,
            "train_loss": round(epoch_loss, 4),
            "val_macro_f1": round(float(macro_f1), 4),
            "val_recall": [round(float(r), 4) for r in rec_per_class],
        })
        print(f"  epoch {epoch:2d}  loss={epoch_loss:.4f}  "
              f"macroF1={macro_f1:.3f}  "
              f"recall[N]={rec_per_class[0]:.3f}  recall[A]={rec_per_class[1]:.3f}")

        if macro_f1 > best_f1:
            best_f1 = float(macro_f1)
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    assert best_state is not None
    model.load_state_dict(best_state)

    print("\n[4/4] Final evaluation on held-out records ...")
    y_true, y_pred, _ = _evaluate(model, test_loader, device)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    report = classification_report(y_true, y_pred, target_names=CLASSES,
                                   digits=3, zero_division=0)
    rec_per_class = recall_score(y_true, y_pred, average=None,
                                 labels=[0, 1]).tolist()
    metrics = {
        "best_val_macro_f1": round(best_f1, 4),
        "final_macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 4),
        "confusion_matrix": cm,
        "recall_normal": round(float(rec_per_class[0]), 4),
        "recall_arrhythmia": round(float(rec_per_class[1]), 4),
        "n_train_windows": int(len(y_train)),
        "n_test_windows": int(len(y_test)),
        "train_records": [f"{db}/{r}" for db, r in train_recs],
        "test_records": [f"{db}/{r}" for db, r in test_recs],
        "history": history,
    }
    print(report)
    print(f"confusion_matrix [Normal, Arrhythmia]:\n{cm}")

    torch.save({
        "model_state": model.state_dict(),
        "classes": list(CLASSES),
        "window_samples": WINDOW_SAMPLES,
        "metrics": metrics,
    }, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved metrics to {METRICS_PATH}")
    return metrics


if __name__ == "__main__":
    train()
