"""
pipeline/contract.py
Single source of truth for the data contract between Layer 2 and Layer 3.
Both the pipeline emitter and the model inference function use this.
"""

from dataclasses import dataclass, field, asdict
from typing import Literal
import json


@dataclass
class ECGWindow:
    """
    The packet emitted by Layer 2 every 2 seconds.
    This is exactly what Layer 3 receives as input.
    """
    clean_ecg: list[float]          # 2500 normalized samples (10s @ 250Hz)
    r_peaks: list[int]              # sample indices of R-peaks within window
    rr_intervals: list[float]       # ms between consecutive R-peaks
    sample_rate: int = 250
    quality: Literal["good", "low", "clipped", "noisy"] = "good"


@dataclass
class InferenceResult:
    """
    The packet emitted by Layer 3 every 2 seconds.
    This is what the dashboard consumes.
    """
    classification: Literal["Normal", "AFib", "Other"]
    confidence: float               # probability of top class [0.0 - 1.0]
    probabilities: dict = field(default_factory=dict)   # {Normal, AFib, Other}
    bpm: float = 0.0                # instantaneous heart rate
    rr_std: float = 0.0             # RR interval std dev (ms) — high = irregular
    quality: str = "good"

    # pass-through for dashboard waveform rendering
    clean_ecg: list[float] = field(default_factory=list)
    r_peaks: list[int] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "InferenceResult":
        return InferenceResult(**json.loads(s))
