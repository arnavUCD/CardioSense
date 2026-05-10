"""CardioSense ML layer: binary ECG arrhythmia classifier."""
from .config import (
    TARGET_FS,
    WINDOW_SECONDS,
    WINDOW_SAMPLES,
    CLASSES,
    MODEL_PATH,
)

__all__ = [
    "TARGET_FS",
    "WINDOW_SECONDS",
    "WINDOW_SAMPLES",
    "CLASSES",
    "MODEL_PATH",
]
