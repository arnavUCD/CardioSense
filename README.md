# CardioSense

**Wearable ECG arrhythmia detection for the people Apple Watch was never designed for.**

A continuous cardiac monitoring system to detect paryoxysmal arrythmia.

Built end-to-end in 24 hours at HackDavis 2026 by a three-person team.

---

## The problem

Most arrhythmias — atrial fibrillation especially — are *paroxysmal*. They come and go unpredictably across hours, days, and weeks. A 12-lead ECG in a clinic captures 10 seconds. By the time a patient sees a cardiologist, the arrhythmia is gone.

For the ~500,000 to 800,000 farmworkers in California (most uninsured, most Spanish-speaking, most working 90+ minutes from the nearest cardiologist), this gap is fatal. AFib alone causes roughly 1 in 7 strokes, and it's silent in the majority of people who have it.

CardioSense closes that gap with a low-cost wearable patch and a continuous monitoring stack that runs end-to-end on a laptop and a phone — no cloud, no subscription, no insurance required.

---

## What we built

A complete four-layer system:


```
                  +----------------------+
                  | Stage 1 (signal sim) |    SignalGenerator/stage1/main.py
                  | reads stage1/mode.txt|    "normal" or "afib"
                  +----------+-----------+
                             | latest_result.json (every 3s)
                             v
                  +----------------------+
                  | Stage 2 (clean+HRV)  |    SignalGenerator/stage2/stage2.py
                  | filter, R-peaks, HRV |
                  +----------+-----------+
                             | stage2/shared/input.json
                             v
                  +----------------------+
                  | ML watcher           |    watch_and_predict.py
                  | 1D-CNN + uncertainty |    cardiosense/
                  +----------+-----------+
                             | shared/prediction.json
                             v
                  +----------------------+
                  | python -m http.server|    served at port 8080
                  +----------+-----------+
                             | http://<mac-ip>:8080/shared/prediction.json
                             v
                  +----------------------+
                  | iOS app (SwiftUI)    |    App/CardioSense/
                  +----------------------+
```



Two interfaces, two audiences, one model: the iOS app for the patient, the Streamlit dashboard for the clinician.

---

## Demo highlights

**The patient view (iOS app)** shows a calm, plain-English readout of the current rhythm — Normal, Arrhythmia detected, Uncertain, or Unknown — with confidence, heart rate, and a clinical explanation. The History tab summarizes events by time range (last 10 min, last hour, last day, last week, last month), so the patient and their clinic can see continuous patterns rather than a single 10-second snapshot.

**The clinician view (Streamlit dashboard)** shows the live ECG waveform, R-peak markers, full HRV metric grid (RMSSD, SDNN, pNN50, mean RR), class probability bars, and signal quality flags. Built for a community-clinic workflow, not a consumer fitness app.

**The model is honest about its limits.** When confidence drops below 60% or signal quality is degraded, the app surfaces an "Uncertain" state and recommends review rather than forcing a Normal/AFib call. The Reference tab in the app explicitly states the system is *"intended for study and monitoring workflows, not as a sole basis for clinical decisions."*

---

## Technical depth

### Hardware
- **MCU:** Arduino Nano 33 BLE (nRF52840, 250 Hz ADC, BLE NOTIFY)
- **Analog Front End:** SparkFun AD8232 single-lead breakout
- **Electrodes:** 3-lead wet gel (RA, LA, RL driven ground)
- **Transport:** 24-byte BLE payload, 10 samples + metadata per 40ms packet

For the demo, a synthetic signal generator emulates the BLE buffer at the same cadence — the downstream pipeline cannot tell the difference. For variety in the demo, **AFib mode plays back real MIT-BIH AFib recordings** (rotated across records 04015, 04043, 06426, 07879, 08455) instead of synthesising AFib morphology. Synthetic AFib is hard to fake convincingly enough for the trained CNN, so we sidestep the issue. Normal mode is fully synthetic. The rotation produces different HR profiles across runs — typically 90–140 bpm, RMSSD 100–300 ms — characteristic of real AFib.

### Signal processing pipeline
- **Filter chain:** 4th-order Butterworth bandpass (1.0–30 Hz), 60 Hz notch, 600ms baseline-wander correction
- **R-peak detection:** Custom Pan-Tompkins implementation in `SignalGenerator/stage2/pipeline/peaks.py` — not a library wrapper
- **HRV features:** SDNN, RMSSD, pNN50, CV, mean RR, mean HR — computed in `SignalGenerator/stage2/pipeline/hrv.py`
- **Window:** 10 seconds, 3-second stride
- **Verified separation:** Normal SDNN ≈ 18ms vs AFib SDNN ≈ 115ms

### ML model
- **Architecture:** Single-branch 1D CNN, 43,362 trainable parameters
- **Input:** (B, 1, 2500) — 10s @ 250Hz, single channel, float32
- **Output:** Binary classifier — Normal vs. Arrhythmia (with runtime-layer Uncertain/Unknown gating)
- **Training data:** MIT-BIH Atrial Fibrillation Database (23 records) + MIT-BIH Arrhythmia Database (48 records, resampled 360→250Hz)
- **Final metrics on held-out records:**


```
              precision    recall  f1-score   support
      Normal      0.913     0.926     0.919      1536
  Arrhythmia      0.904     0.887     0.895      1205
    accuracy                          0.909      2741
```



Both class recalls clear the ≥0.85 hackathon target. On 100 stratified held-out clips: **97% accuracy** (95% with the Uncertain gate engaged as a strict safety filter).

- **Inference latency:** ~10ms on Apple MPS, ~25–35ms on CPU
- **Confidence handling:** Predictions below 60% confidence are surfaced as "Uncertain" rather than forcing a binary call

### iOS app
- **Stack:** Native Swift, SwiftUI, dark clinical theme
- **Polling:** 2-second cadence against the prediction endpoint
- **Tabs:** Monitor (live status), History (time-range filtered events), Reference (educational copy with confidence and HRV explanations), Samples (developer test harness shipped in production)
- **Designed for the patient-clinic workflow:** patient sees calm, actionable readouts; clinic sees continuous-monitoring history with state-transition events

### Streamlit dashboards
- Stage 1 (raw signal): live ECG, rhythm picker (Normal/AFib toggle), confidence, BPM, RR variability
- Stage 2 (cleaned signal): cleaned ECG with R-peak markers, HRV metric grid, raw-vs-cleaned comparison

---

## Output schema (what the iOS app consumes)


```json
{
  "label": "Arrhythmia",          // "Normal" | "Arrhythmia" | "Uncertain" | "Unknown"
  "raw_label": "Arrhythmia",      // model's underlying verdict
  "confidence": 0.91,
  "probabilities": { "Normal": 0.09, "Arrhythmia": 0.91 },
  "arrhythmia_detected": true,
  "is_uncertain": false,
  "quality": { "ok": true, "reasons": [] },
  "heart_rate": 118.0,
  "hrv": { "rmssd": 18.4, "sdnn": 52.1, "pnn50": 0.34, "mean_rr_ms": 508.0 },
  "sample_rate": 250,
  "window_seconds": 10,
  "n_windows": 5,
  "n_r_peaks": 58
}
```



`label = "Uncertain"` is emitted when model confidence < 0.6 OR R-peaks can't be detected OR the signal is flat. `quality.reasons` enumerates the cause(s). Numeric fields can be `null` (never `NaN`).

---

## Repository structure


```
cardiosense/             # ML layer (training + inference)
  config.py              # constants, rhythm map, uncertainty threshold
  signal_utils.py        # bandpass, R-peak detector, HRV, resampling
  data.py                # window-builder for MIT-BIH AFib + Arrhythmia DBs
  model.py               # compact 1D CNN, ~43k params
  train.py               # training loop + record-level split
  predict.py             # predict_ecg() — accepts CSV/JSON/dict/array
  stream.py              # rolling-buffer streaming wrapper
SignalGenerator/
  stage1/                # simulated BLE ECG stream + dashboard
  stage2/                # filter + R-peak + HRV pipeline + dashboard
App/                     # SwiftUI iOS app (Xcode project)
shared/                  # prediction.json (served over HTTP)
raw/                     # MIT-BIH datasets (gitignored)
artifacts/               # trained model + metrics
watch_and_predict.py     # bridge: stage2 -> ML -> shared/prediction.json
run_demo.sh              # one-shot launcher for the full pipeline
```



---

## How to run it

### Prerequisites
- macOS (tested on Apple Silicon, MPS-accelerated)
- Python 3.10
- Xcode 15+ (for the iOS app)
- An iPhone on the same Wi-Fi network as the Mac

### One-time setup


```bash
git clone https://github.com/vcro45/CardioSense.git
cd CardioSense

python3.10 -m venv .venv
source .venv/bin/activate
pip install numpy pandas scipy scikit-learn torch streamlit plotly
```



(streamlit + plotly are only needed if you want the live dashboards; the core pipeline runs without them.)

### Train the model


```bash
.venv/bin/python -m cardiosense.train
```



Reads MIT-BIH AFib + Arrhythmia DBs from `raw/`, splits at the **record level** (no leakage), writes `artifacts/model.pt` and `artifacts/metrics.json`.

### Run the full demo

Open four terminal tabs in the project root.

**Tab 1 — full pipeline (Stage 1 + Stage 2 + ML watcher + HTTP server):**

```bash
./run_demo.sh
```


Prints the Mac LAN IP for the iPhone, starts all four background processes, tails the watcher's log. Per-stage logs go to `logs/`. Ctrl+C cleans up everything.

**Tab 2 — Stage 1 dashboard (rhythm picker):**

```bash
source .venv/bin/activate
streamlit run SignalGenerator/stage1/dashboard.py --server.port 8501
```


Open http://localhost:8501. Sidebar Normal/AFib toggle writes `SignalGenerator/stage1/mode.txt` — Stage 1 picks it up within ~1 second and the rest of the pipeline follows.

**Tab 3 — Stage 2 dashboard (cleaned signal + HRV):**

```bash
source .venv/bin/activate
streamlit run SignalGenerator/stage2/dashboard2.py --server.port 8502
```


Open http://localhost:8502. Visualises the cleaned ECG, R-peaks, and HRV stats fed into the model.

**Tab 4 — iPhone app:**
1. Open `App/CardioSense.xcodeproj` in Xcode
2. Find your Mac's local IP: `ipconfig getifaddr en0`
3. Build and run on a connected iPhone on the same Wi-Fi
4. In the app: tap the gear icon → set Prediction URL to `http://<your-mac-ip>:8080/shared/prediction.json`
5. The app starts polling every 2 seconds

### Toggling rhythm without the dashboard


```bash
echo "afib"   > SignalGenerator/stage1/mode.txt
echo "normal" > SignalGenerator/stage1/mode.txt
```



Each switch takes ~10 seconds to fully transition (Stage 1's rolling buffer turnover).

### ML layer alone — without the signal generator

If you just want to run inference on a CSV / JSON file:


```bash
.venv/bin/python predict_cli.py recording.csv --sample-rate 250
.venv/bin/python predict_cli.py recording.json
```



Or from Python:


```python
from cardiosense.predict import predict_ecg

predict_ecg([0.12, 0.13, ...], sample_rate=250)
predict_ecg({"clean_ecg": [...], "sample_rate": 250})
predict_ecg("recording.csv", sample_rate=250)
predict_ecg("recording.json")
```



For continuous chunked input:


```python
from cardiosense.stream import ECGStream
stream = ECGStream(sample_rate=250, step_seconds=2.0)
for chunk in chunks:
    result = stream.push(chunk)
    if result is not None:
        send_to_frontend(result)
```



### Stopping everything


```bash
# from the run_demo.sh terminal
Ctrl+C

# nuclear option
pkill -f "main.py"; pkill -f "stage2.py"; pkill -f "watch_and_predict.py"
pkill -f "http.server"; pkill -f "streamlit"
```



### Validation


```bash
# 100 held-out clips stratified across both DBs
.venv/bin/python -m scripts.validate_100

# 22 named held-out records, one Normal + one AFib clip each
.venv/bin/python -m scripts.sanity_test
```


---

## What this is not

We are deliberate about scope:

- **Not FDA-cleared.** The system is a research and monitoring tool, not a diagnostic device. The app states this explicitly.
- **Not a replacement for a cardiologist.** It surfaces patterns; clinicians make decisions.
- **Not trained on patch-derived data.** The model was trained on MIT-BIH clinical recordings. Performance on real patch data would need additional validation before any deployment.
- **Not a consumer health app.** No streaks, no gamification, no daily summaries. It's medical software designed for serious use.

---

## Team

Three students at UC Davis. Hardware and signal processing by our EE lead. Machine learning model by our ML engineer. iOS app, signal pipeline, dashboards, and product design by our software lead.

Built end-to-end in 24 hours on May 9–10, 2026.

---

## Acknowledgments

- **MIT-BIH Atrial Fibrillation Database** and **MIT-BIH Arrhythmia Database** — PhysioNet
- **HackDavis 2026** organizers and judges
- **Communicare Health Centers** (Yolo County) and **Clínica Tepati** (Sacramento) — community clinics that serve the populations this project is designed for, and the model for the kind of partner this system is built to support

---

*If you build something that uses this, deploy it where it actually matters, or want to talk about cardiac monitoring for underserved populations — open an issue.*
