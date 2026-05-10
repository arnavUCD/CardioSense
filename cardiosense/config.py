"""Shared constants for CardioSense."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "raw"
AFIB_DIR = RAW_DIR / "MIT-BIH Atrial Fibrillation Database"
ARRHYTHMIA_DIR = RAW_DIR / "MIT-BIH Arrhythmia Database"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

# Fixed working sample rate. AFib DB is 250 Hz; Arrhythmia DB is 360 Hz —
# both are resampled to TARGET_FS before training and inference.
TARGET_FS = 250
AFIB_FS = 250
ARRHYTHMIA_FS = 360

WINDOW_SECONDS = 10
WINDOW_SAMPLES = TARGET_FS * WINDOW_SECONDS  # 2500

CLASSES = ("Normal", "Arrhythmia")
NUM_CLASSES = len(CLASSES)
UNCERTAIN_LABEL = "Uncertain"

# Confidence below which the model abstains and emits "Uncertain".
UNCERTAIN_CONFIDENCE = 0.6

# Rhythm aux_note -> binary label.
# Both databases are merged here. The Arrhythmia DB uses a "(N0" style with
# trailing channel digit; the AFib DB uses "(N". We accept both forms.
RHYTHM_TO_LABEL = {
    # Normal sinus rhythm
    "(N":     0, "(N0":     0,
    # Atrial fibrillation
    "(AFIB":  1, "(AFIB0":  1,
    # Atrial flutter
    "(AFL":   1, "(AFL0":   1,
    # Junctional / nodal rhythms
    "(J":     1,
    "(NOD0":  1,
    # Supraventricular tachyarrhythmia
    "(SVTA":  1, "(SVTA0":  1,
    # Ventricular tachy / flutter / idioventricular
    "(VT0":   1,
    "(VFL0":  1,
    "(IVR0":  1,
    # Bigeminy / trigeminy / atrial bigeminy
    "(B0":    1,
    "(T0":    1,
    "(AB0":   1,
    # Heart block, sinus brady
    "(BII0":  1,
    "(SBR0":  1,
}

# Rhythms we explicitly drop (artifacts / paced beats / non-physiologic).
SKIP_RHYTHMS = {
    "(P", "(P0",       # paced rhythm
    "(PREX0",          # WPW pre-excitation
    "MISSB0",          # missed beat marker
    "TS0",             # tape slippage
    "PSE0",            # pause
}

# Cap windows per record per class to balance the dataset and keep training quick.
MAX_WINDOWS_PER_RECORD_PER_CLASS = 150

MODEL_PATH = ARTIFACTS_DIR / "model.pt"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
