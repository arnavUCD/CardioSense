"""
synthetic_generator.py
Generates a realistic noisy ECG signal mimicking raw hardware output
before any filtering. Layered noise: baseline wander, powerline, gaussian,
and occasional motion artifact bursts.

Normal rhythm: fully synthetic.
AFib rhythm: plays back a slice of real MIT-BIH AFib data (so the trained
CNN reliably detects it on demo). Synthetic AFib morphology is only an
approximation; real f-waves are hard to fake well enough.
"""

import os
from pathlib import Path

import numpy as np

# Cached real-AFib clips from the MIT-BIH Atrial Fibrillation Database.
# Loaded lazily on the first afib request and reused across calls. We cache
# multiple records with different HR profiles so repeated AFib demos show
# variety in heart-rate / morphology rather than the same loop every time.
_AFIB_POOLS: list[np.ndarray] | None = None

# Records picked for variety in HR and AFib presentation. All have at least
# one (AFIB rhythm interval longer than 30 seconds.
_AFIB_RECORDS = ["04015", "04043", "06426", "07879", "08455"]
_AFIB_CLIP_SECONDS = 60  # how much of each record to cache


def _project_root() -> Path:
    """Walk up from this file until we find raw/MIT-BIH Atrial Fibrillation Database."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "raw" / "MIT-BIH Atrial Fibrillation Database").exists():
            return parent
    return here.parents[3]  # fallback (project root, 3 levels up from this file)


def _load_one_afib_record(record: str, afib_dir: Path,
                          target_seconds: int = _AFIB_CLIP_SECONDS) -> np.ndarray:
    """Load a contiguous AFib clip from the longest (AFIB interval in `record`."""
    import json, ast, csv
    ann = json.loads((afib_dir / f"{record}_annotations.json").read_text())
    samples = ast.literal_eval(ann["sample"])
    notes = ann["aux_note"]
    # find the longest "(AFIB" interval
    best = (0, 0, 0)  # (length, start, end)
    for i, (s, n) in enumerate(zip(samples, notes)):
        if n != "(AFIB":
            continue
        end = samples[i + 1] if i + 1 < len(samples) else 9_000_000
        if end - s > best[0]:
            best = (end - s, s, end)
    length, start, end = best
    if length == 0:
        return np.empty(0, dtype=np.float32)
    take = min(end - start, target_seconds * 250)
    pool = np.empty(take, dtype=np.float32)
    with open(afib_dir / f"{record}_ekg.csv") as f:
        reader = csv.reader(f)
        header = next(reader)
        ecg1_col = header.index("ECG1")
        for _ in range(start):
            next(reader, None)
        for i in range(take):
            row = next(reader, None)
            if row is None:
                pool = pool[:i]
                break
            pool[i] = float(row[ecg1_col])
    return pool


def _load_real_afib_pool() -> np.ndarray:
    """Return one of the cached real-AFib clips, picked at random per call.

    First call loads all the records in `_AFIB_RECORDS` (each ~60 s of real
    AFib). Subsequent calls just pick one. Each rhythm switch in Stage 1
    triggers one call, so successive AFib demos show different HR profiles.
    """
    global _AFIB_POOLS
    if _AFIB_POOLS is None:
        afib_dir = _project_root() / "raw" / "MIT-BIH Atrial Fibrillation Database"
        pools = []
        for rec in _AFIB_RECORDS:
            try:
                clip = _load_one_afib_record(rec, afib_dir)
                if len(clip) >= 30 * 250:  # at least 30 s usable
                    pools.append(clip)
            except Exception as e:
                print(f"[generator] skipping AFib record {rec}: {e}")
        if not pools:
            raise RuntimeError("no AFib data available")
        _AFIB_POOLS = pools
        print(f"[generator] cached {len(pools)} real-AFib clips "
              f"({sum(len(p) for p in pools) / 250:.0f}s total)")
    return _AFIB_POOLS[np.random.randint(0, len(_AFIB_POOLS))]


def generate_qrs_template(sample_rate: int = 250,
                          with_p_wave: bool = True) -> np.ndarray:
    """
    Build a single clean QRS complex using gaussian curves.
    Returns one beat's worth of samples centered on the R-peak.

    `with_p_wave=False` produces an AFib-like beat: P-waves are absent
    in atrial fibrillation because the atria fibrillate instead of
    contracting, so the trained model expects them to be missing.
    """
    duration = int(0.6 * sample_rate)  # 600ms per beat template
    t = np.linspace(-0.3, 0.3, duration)

    p_wave = (0.15 * np.exp(-((t + 0.18) ** 2) / (2 * 0.012 ** 2))
              if with_p_wave else np.zeros_like(t))
    q_wave = -0.08 * np.exp(-((t + 0.03) ** 2) / (2 * 0.005 ** 2))
    r_wave = 1.0 * np.exp(-(t ** 2) / (2 * 0.008 ** 2))
    s_wave = -0.15 * np.exp(-((t - 0.04) ** 2) / (2 * 0.007 ** 2))
    t_wave = 0.25 * np.exp(-((t - 0.15) ** 2) / (2 * 0.025 ** 2))

    return p_wave + q_wave + r_wave + s_wave + t_wave


def generate_fibrillation_waves(n_samples: int, sample_rate: int = 250,
                                amplitude: float = 0.20) -> np.ndarray:
    """
    Generate atrial fibrillation 'f-waves': chaotic oscillations on
    the baseline at ~4-9 Hz. These replace the absent P-waves in real
    AFib and are a key feature the trained CNN looks for.

    We start from white noise and bandpass-filter it to the f-wave band,
    which yields the irregular, never-quite-periodic shape real AFib has
    (a sum of sinusoids stays too smooth).
    """
    from scipy.signal import butter, filtfilt
    raw = np.random.randn(n_samples)
    nyq = sample_rate / 2.0
    b, a = butter(3, [4.0 / nyq, 9.0 / nyq], btype="band")
    waves = filtfilt(b, a, raw)
    # normalise so amplitude has a meaningful unit (peak ≈ amplitude)
    peak = max(float(np.abs(waves).max()), 1e-6)
    return amplitude * waves / peak


def generate_clean_ecg(
    duration_s: float = 30.0,
    heart_rate_bpm: float = 72.0,
    sample_rate: int = 250,
    rhythm: str = "normal",  # "normal" or "afib"
) -> tuple[np.ndarray, list[int]]:
    """
    Generate a clean synthetic ECG signal with realistic beat placement.
    Returns (signal array, list of R-peak sample indices).
    """
    n_samples = int(duration_s * sample_rate)

    # AFib path: use real MIT-BIH AFib data as the source-of-truth signal.
    # Synthetic AFib morphology (absent P + f-waves) is hard to fake well
    # enough for the trained CNN, so we play back real AFib instead. This
    # makes the demo reliably flip Normal -> Arrhythmia when the user
    # toggles rhythm in the dashboard.
    if rhythm == "afib":
        try:
            pool = _load_real_afib_pool()
            if len(pool) >= n_samples:
                offset = np.random.randint(0, len(pool) - n_samples + 1)
                clip = pool[offset:offset + n_samples].astype(np.float32)
            else:
                # tile if pool is shorter than the requested duration
                reps = int(np.ceil(n_samples / max(len(pool), 1)))
                clip = np.tile(pool, reps)[:n_samples].astype(np.float32)
            # detect approximate R-peaks for downstream consumers
            from scipy.signal import find_peaks
            thr = 0.6 * float(np.max(np.abs(clip)))
            peaks, _ = find_peaks(clip, height=thr, distance=int(0.25 * sample_rate))
            return clip, list(peaks.astype(int))
        except Exception:
            # If anything goes wrong loading real data, fall through to the
            # synthetic AFib approximation below (better than crashing).
            pass

    signal = np.zeros(n_samples)
    r_peaks = []

    # Synthetic path. AFib synthetic fallback drops the P-wave and lays
    # f-waves on the baseline — used only if real-data load failed.
    is_afib = (rhythm == "afib")
    template = generate_qrs_template(sample_rate, with_p_wave=not is_afib)
    half = len(template) // 2

    if is_afib:
        signal += generate_fibrillation_waves(n_samples, sample_rate)

    # Beat interval with variability
    base_interval = int(60.0 / heart_rate_bpm * sample_rate)

    pos = base_interval
    while pos < n_samples - half:
        if rhythm == "afib":
            # AFib: irregularly irregular — high variance in RR intervals
            jitter = int(np.random.uniform(-0.25, 0.25) * base_interval)
        else:
            # Normal sinus: small physiological variability
            jitter = int(np.random.normal(0, 0.02 * base_interval))

        interval = base_interval + jitter
        interval = max(int(0.5 * base_interval), min(int(1.5 * base_interval), interval))

        r_peak_idx = pos
        start = r_peak_idx - half
        end = start + len(template)

        if end <= n_samples:
            # Beat-to-beat amplitude variation: minor in normal, moderate in
            # AFib (the irregular ventricular response affects QRS height too).
            amp_jitter = (np.random.uniform(0.85, 1.10) if is_afib
                          else np.random.uniform(0.95, 1.05))
            signal[start:end] += amp_jitter * template
            r_peaks.append(r_peak_idx)

        pos += interval

    return signal, r_peaks


def add_noise(
    clean_signal: np.ndarray,
    sample_rate: int = 250,
    baseline_wander_amp: float = 0.3,
    powerline_amp: float = 0.15,
    gaussian_std: float = 0.08,
    motion_artifact_prob: float = 0.03,
) -> np.ndarray:
    """
    Layer realistic hardware noise onto a clean ECG signal.

    Layers:
      1. Baseline wander    — slow breathing-frequency undulation (~0.3 Hz)
      2. Powerline noise    — 60 Hz sinusoid
      3. Gaussian noise     — random sample-level jitter
      4. Motion artifacts   — occasional high-amplitude bursts
    """
    n = len(clean_signal)
    t = np.arange(n) / sample_rate
    noisy = clean_signal.copy()

    # 1. Baseline wander (breathing: ~0.25 Hz with slight drift)
    wander_freq = 0.25 + np.random.uniform(-0.05, 0.05)
    wander = baseline_wander_amp * np.sin(2 * np.pi * wander_freq * t)
    wander += 0.1 * baseline_wander_amp * np.sin(2 * np.pi * 0.1 * t)
    noisy += wander

    # 2. Powerline interference (60 Hz)
    powerline = powerline_amp * np.sin(2 * np.pi * 60 * t)
    noisy += powerline

    # 3. Gaussian noise (electrode + amplifier noise)
    noisy += np.random.normal(0, gaussian_std, n)

    # 4. Motion artifact bursts (short high-amplitude transients)
    burst_samples = int(0.2 * sample_rate)  # 200ms bursts
    for i in range(n - burst_samples):
        if np.random.random() < motion_artifact_prob / sample_rate:
            burst_amp = np.random.uniform(0.5, 1.5)
            burst = burst_amp * np.random.normal(0, 1, burst_samples)
            # smooth edges so it doesn't look like a digital glitch
            fade = np.hanning(burst_samples)
            noisy[i:i + burst_samples] += burst * fade

    return noisy


def generate_noisy_ecg(
    duration_s: float = 60.0,
    heart_rate_bpm: float = 72.0,
    sample_rate: int = 250,
    rhythm: str = "normal",
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """
    Main entry point. Returns:
      - noisy_signal   : raw hardware-like ECG [n_samples]
      - clean_signal   : ground-truth clean ECG [n_samples]
      - r_peaks        : ground-truth R-peak indices
    """
    clean_signal, r_peaks = generate_clean_ecg(
        duration_s=duration_s,
        heart_rate_bpm=heart_rate_bpm,
        sample_rate=sample_rate,
        rhythm=rhythm,
    )

    if rhythm == "afib":
        # Real MIT-BIH AFib already contains realistic baseline wander and
        # measurement noise — adding the synthetic noise layer on top drowns
        # the f-waves the model relies on. Add only a very mild gaussian
        # jitter so it still looks "live" rather than perfectly clean.
        noisy_signal = clean_signal + np.random.normal(
            0, 0.01, size=len(clean_signal)
        )
    else:
        noisy_signal = add_noise(clean_signal, sample_rate=sample_rate)

    return noisy_signal, clean_signal, r_peaks


if __name__ == "__main__":
    # Quick sanity check — print signal stats
    noisy, clean, peaks = generate_noisy_ecg(duration_s=10.0, rhythm="normal")
    print(f"Generated {len(noisy)} samples ({len(noisy)/250:.1f}s)")
    print(f"R-peaks found: {len(peaks)} (expected ~{int(10 * 72/60)})")
    print(f"Noisy signal range: [{noisy.min():.3f}, {noisy.max():.3f}]")
    print(f"Clean signal range: [{clean.min():.3f}, {clean.max():.3f}]")
