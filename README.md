# CardioSense

A wearable-style ECG arrhythmia monitor end-to-end demo: synthetic ECG
stream → signal cleaning → ML classification → live iOS dashboard.

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
                             | http://10.0.0.29:8080/shared/prediction.json
                             v
                  +----------------------+
                  | iOS app (SwiftUI)    |    App/CardioSense/
                  +----------------------+
```

## Repo layout

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
  stage1/                # simulated BLE ECG stream
  stage2/                # filter + R-peak + HRV pipeline
App/                     # SwiftUI iOS app
shared/                  # prediction.json (served over HTTP)
raw/                     # MIT-BIH AFib + Arrhythmia datasets
artifacts/               # trained model + metrics
watch_and_predict.py     # bridge: reads stage2/shared/input.json -> shared/prediction.json
run_demo.sh              # one-shot launcher for the full pipeline
```

## One-time setup

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install numpy pandas scipy scikit-learn torch streamlit plotly
```

(streamlit + plotly are only needed if you want the live dashboards; the
core pipeline runs without them.)

## Train the model

```bash
.venv/bin/python -m cardiosense.train
```

Reads MIT-BIH AFib + Arrhythmia DBs from `raw/`, splits at the **record
level** (no leakage), writes `artifacts/model.pt` and `artifacts/metrics.json`.

Latest run:

```
              precision    recall  f1-score   support
      Normal      0.913     0.926     0.919      1536
  Arrhythmia      0.904     0.887     0.895      1205
    accuracy                          0.909      2741
```

Both Normal and Arrhythmia recall clear the ≥0.85 hackathon target. On
100 stratified held-out clips: **97% accuracy** (95% with the Uncertain
gate engaged as a strict safety filter).

## Run the full demo

Open four terminal tabs in the project root.

### Tab 1 — full pipeline (Stage 1 + Stage 2 + ML watcher + HTTP server)

```bash
./run_demo.sh
```

Prints the Mac LAN IP for the iPhone, starts all four background
processes, tails the watcher's log. Per-stage logs go to `logs/`.
Ctrl+C cleans up everything.

### Tab 2 — Stage 1 dashboard (rhythm picker)

```bash
source .venv/bin/activate
streamlit run SignalGenerator/stage1/dashboard.py --server.port 8501
```

Open <http://localhost:8501>. Sidebar Normal/AFib toggle writes
`SignalGenerator/stage1/mode.txt` — Stage 1 picks it up within ~1
second and the rest of the pipeline follows.

### Tab 3 — Stage 2 dashboard (cleaned signal + HRV)

```bash
source .venv/bin/activate
streamlit run SignalGenerator/stage2/dashboard2.py --server.port 8502
```

Open <http://localhost:8502>. Visualises the cleaned ECG, R-peaks,
and HRV stats fed into the model.

### Tab 4 — iPhone app

Build & run from Xcode on a device on the same Wi-Fi as the Mac.
The app fetches `http://10.0.0.29:8080/shared/prediction.json` every 2
seconds and updates the dashboard. If your Mac IP differs, edit it in
the app's connection bar (no rebuild required).

## Toggling rhythm without the dashboard

```bash
echo "afib"   > SignalGenerator/stage1/mode.txt
echo "normal" > SignalGenerator/stage1/mode.txt
```

Each switch takes ~10 seconds to fully transition (Stage 1's rolling
buffer turnover).

## How the AFib path works

For variety in the demo, **AFib mode plays back real MIT-BIH AFib
recordings** (rotated across records `04015, 04043, 06426, 07879,
08455`) instead of synthesising AFib morphology. Synthetic AFib
(irregular RR + missing P-waves + f-waves) is hard to fake convincingly
enough for the trained CNN, so we sidestep the issue. Normal mode is
fully synthetic.

The rotation gives different HR profiles across runs — typically
90–140 bpm, RMSSD 100–300 ms — characteristic of real AFib.

## Output schema (what the iOS app consumes)

```json
{
  "label": "Arrhythmia",          // "Normal" | "Arrhythmia" | "Uncertain" | "Unknown"
  "raw_label": "Arrhythmia",      // model's underlying verdict ("Normal" or "Arrhythmia")
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

`label = "Uncertain"` is emitted when model confidence < 0.6 OR R-peaks
can't be detected OR the signal is flat. `quality.reasons` enumerates
the cause(s). Numeric fields can be `null` (never `NaN`).

## ML layer alone — without the signal generator

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

## Stopping everything

```bash
# from the run_demo.sh terminal
Ctrl+C

# from a streamlit terminal
Ctrl+C

# nuclear option
pkill -f "main.py"; pkill -f "stage2.py"; pkill -f "watch_and_predict.py"
pkill -f "http.server"; pkill -f "streamlit"
```

## Validation

```bash
# 100 held-out clips stratified across both DBs
.venv/bin/python -m scripts.validate_100

# 22 named held-out records, one Normal + one AFib clip each
.venv/bin/python -m scripts.sanity_test
```
