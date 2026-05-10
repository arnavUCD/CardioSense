"""Streaming wrapper around `predict_ecg`.

For producers that push ECG samples in JSON chunks (e.g. one chunk per
second from the signal-processing layer). Buffers samples, runs the model
every `step_seconds`, and emits the same JSON dict the one-shot API
returns.

Typical use (single-patient stream):

    stream = ECGStream(sample_rate=250, window_seconds=10, step_seconds=2)
    for chunk in incoming_json_chunks:
        result = stream.push(chunk)        # returns dict OR None
        if result is not None:
            send_to_frontend(result)
"""
from __future__ import annotations

from collections import deque
from typing import Any, Iterable

import numpy as np

from .config import TARGET_FS, WINDOW_SECONDS
from .predict import predict_ecg


def _extract_samples(chunk: Any) -> np.ndarray:
    """Pull ECG samples out of a JSON chunk in any of the supported shapes."""
    if isinstance(chunk, (list, tuple, np.ndarray)):
        return np.asarray(chunk, dtype=np.float32)
    if isinstance(chunk, dict):
        for key in ("clean_ecg", "ecg", "signal", "samples", "values"):
            if key in chunk:
                return np.asarray(chunk[key], dtype=np.float32)
    raise ValueError(
        f"chunk has no recognised ECG field. "
        f"Expected one of clean_ecg/ecg/signal/samples/values, got: "
        f"{list(chunk.keys()) if isinstance(chunk, dict) else type(chunk).__name__}"
    )


class ECGStream:
    """Rolling buffer that runs predict_ecg every `step_seconds`."""

    def __init__(self,
                 sample_rate: int = TARGET_FS,
                 window_seconds: int = WINDOW_SECONDS,
                 step_seconds: float = 2.0,
                 max_buffer_seconds: float | None = None):
        self.sample_rate = int(sample_rate)
        self.window_samples = int(window_seconds * self.sample_rate)
        self.step_samples = max(1, int(step_seconds * self.sample_rate))
        # Keep a rolling buffer; cap it so memory doesn't grow unbounded.
        max_buf = max_buffer_seconds or (window_seconds * 3)
        self._buf: deque[float] = deque(maxlen=int(max_buf * self.sample_rate))
        self._samples_since_last_pred = 0

    def push(self, chunk: Any) -> dict | None:
        """Add a chunk. Returns a prediction dict when due, else None."""
        samples = _extract_samples(chunk)
        self._buf.extend(samples.tolist())
        self._samples_since_last_pred += len(samples)

        if len(self._buf) < self.window_samples:
            return None
        if self._samples_since_last_pred < self.step_samples:
            return None

        self._samples_since_last_pred = 0
        window = np.fromiter(
            (self._buf[i] for i in range(len(self._buf) - self.window_samples,
                                         len(self._buf))),
            dtype=np.float32,
            count=self.window_samples,
        )
        return predict_ecg(window, sample_rate=self.sample_rate)

    def reset(self) -> None:
        self._buf.clear()
        self._samples_since_last_pred = 0


def predict_stream(chunks: Iterable[Any], **kwargs) -> Iterable[dict]:
    """Convenience generator: yield a result for every emitted prediction."""
    stream = ECGStream(**kwargs)
    for chunk in chunks:
        out = stream.push(chunk)
        if out is not None:
            yield out
