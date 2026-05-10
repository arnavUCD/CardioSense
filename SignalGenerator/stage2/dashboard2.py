"""
dashboard2.py — Stage 2 live dashboard.
Reads shared/input.json written by stage2.py.

Run with:
    streamlit run dashboard2.py --server.port 8502
"""

import json, time, os
from collections import deque
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Stage 2 — Cleaned ECG",
                   page_icon="📡", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
  .stApp { background-color: #0d1117; color: #e6edf3; }
  div[data-testid="metric-container"] {
    background:#161b22; border:1px solid #21262d;
    border-radius:12px; padding:14px 18px;
  }
  div[data-testid="metric-container"] label {
    color:#8b949e !important; font-size:11px !important;
    letter-spacing:0.08em; text-transform:uppercase;
  }
  div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-size:22px !important; font-weight:500 !important;
  }
  .afib-banner {
    background:#3d1f1f; border:1px solid #f85149; border-radius:10px;
    padding:10px 18px; color:#f85149; font-weight:500; font-size:15px;
    text-align:center; margin-bottom:8px;
  }
  .normal-banner {
    background:#1a2f1a; border:1px solid #3fb950; border-radius:10px;
    padding:10px 18px; color:#3fb950; font-weight:500; font-size:15px;
    text-align:center; margin-bottom:8px;
  }
  .section-label {
    color:#8b949e; font-size:11px; letter-spacing:0.1em;
    text-transform:uppercase; margin-bottom:4px; margin-top:16px;
  }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding-top:1.5rem; padding-bottom:1rem; }
</style>
""", unsafe_allow_html=True)

# ── Paths — look for shared/input.json relative to this file ─────────────────
BASE       = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(BASE, "shared", "input.json")
# Also try stage1 folder for raw signal display
STAGE1_DIR = os.path.join(BASE, "..", "stage1")
RAW_FILE   = os.path.join(STAGE1_DIR, "latest_result.json")

ECG_DISPLAY = 750

for key, val in [
    ("clean_buf", deque(maxlen=ECG_DISPLAY)),
    ("raw_buf",   deque(maxlen=ECG_DISPLAY)),
    ("rr_hist",   deque(maxlen=40)),
    ("sdnn_hist", deque(maxlen=40)),
    ("hr_hist",   deque(maxlen=40)),
]:
    if key not in st.session_state:
        st.session_state[key] = val


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


cleaned  = load(MODEL_FILE)
raw_data = load(RAW_FILE)
connected = cleaned is not None

if cleaned:
    st.session_state.clean_buf = deque(cleaned.get("clean_ecg", [])[-ECG_DISPLAY:], maxlen=ECG_DISPLAY)
    rr = cleaned.get("rr_intervals", [])
    if rr:
        st.session_state.rr_hist.extend(rr)
    hrv = cleaned.get("hrv_features", {})
    if hrv.get("sdnn", 0) > 0:
        st.session_state.sdnn_hist.append(hrv["sdnn"])
        st.session_state.hr_hist.append(hrv["mean_hr"])

if raw_data:
    st.session_state.raw_buf = deque(raw_data.get("clean_ecg", [])[-ECG_DISPLAY:], maxlen=ECG_DISPLAY)

rhythm = cleaned.get("rhythm_mode", "normal") if cleaned else "normal"
hrv    = cleaned.get("hrv_features", {}) if cleaned else {}
info   = cleaned.get("window_info", {}) if cleaned else {}
color  = "#3fb950" if rhythm == "normal" else "#f85149"
cfill  = "rgba(63,185,80,0.08)" if rhythm == "normal" else "rgba(248,81,73,0.08)"


def ecg_plot(samples, r_peaks, line_color, title="", key=""):
    if not samples:
        return go.Figure()
    x = [i / 250 for i in range(len(samples))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=samples, mode="lines",
        line=dict(color=line_color, width=1.4), hoverinfo="skip"))
    valid = [p for p in r_peaks if 0 <= p < len(samples)]
    if valid:
        fig.add_trace(go.Scatter(
            x=[p/250 for p in valid], y=[samples[p] for p in valid],
            mode="markers",
            marker=dict(color="#f0883e", size=7, symbol="triangle-down"),
            hoverinfo="skip"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
        margin=dict(l=8,r=8,t=28,b=8), height=190, showlegend=False,
        title=dict(text=title, font=dict(color="#8b949e", size=11), x=0),
        xaxis=dict(showgrid=True, gridcolor="#21262d", gridwidth=0.5,
                   zeroline=False, tickfont=dict(color="#8b949e", size=10),
                   title=dict(text="time (s)", font=dict(color="#8b949e", size=10))),
        yaxis=dict(showgrid=True, gridcolor="#21262d", gridwidth=0.5,
                   zeroline=True, zerolinecolor="#30363d", showticklabels=False))
    return fig


def line_plot(y_vals, line_color, fill_color, title="", y_label="", hline=None, hline_label=""):
    if not y_vals:
        return go.Figure()
    fig = go.Figure()
    if hline:
        fig.add_hline(y=hline, line_dash="dot", line_color="#444c56", line_width=1,
                      annotation_text=hline_label,
                      annotation_font=dict(color="#555d68", size=10))
    fig.add_trace(go.Scatter(
        x=list(range(len(y_vals))), y=list(y_vals),
        mode="lines+markers",
        line=dict(color=line_color, width=1.5),
        marker=dict(color=line_color, size=4),
        fill="tozeroy", fillcolor=fill_color,
        hovertemplate=f"%{{y:.1f}} {y_label}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
        margin=dict(l=8,r=8,t=28,b=8), height=160, showlegend=False,
        title=dict(text=title, font=dict(color="#8b949e", size=11), x=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="#21262d", gridwidth=0.5,
                   zeroline=False, tickfont=dict(color="#8b949e", size=10),
                   title=dict(text=y_label, font=dict(color="#8b949e", size=10))))
    return fig


def rr_plot(rr_vals, line_color, fill_color):
    if not rr_vals:
        return go.Figure()
    vals = list(rr_vals)
    mean_rr = sum(vals) / len(vals)
    fig = go.Figure()
    fig.add_hline(y=mean_rr, line_dash="dot", line_color="#444c56", line_width=1,
                  annotation_text=f"mean {mean_rr:.0f}ms",
                  annotation_font=dict(color="#555d68", size=10))
    fig.add_trace(go.Scatter(
        x=list(range(len(vals))), y=vals,
        mode="lines+markers",
        line=dict(color=line_color, width=1.5),
        marker=dict(color=line_color, size=4),
        fill="tozeroy", fillcolor=fill_color,
        hovertemplate="%{y:.0f} ms<extra></extra>"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
        margin=dict(l=8,r=8,t=28,b=8), height=160, showlegend=False,
        title=dict(text="RR interval history", font=dict(color="#8b949e", size=11), x=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="#21262d", gridwidth=0.5,
                   zeroline=False, tickfont=dict(color="#8b949e", size=10),
                   title=dict(text="ms", font=dict(color="#8b949e", size=10))))
    return fig


# ── Layout ────────────────────────────────────────────────────────────────────
h1, h2 = st.columns([5,1])
with h1:
    st.markdown("## Stage 2 — Cleaned ECG Signal")
with h2:
    st.markdown(
        f"<div style='text-align:right;padding-top:20px;font-size:13px;color:#8b949e'>"
        f"{'🟢 Live' if connected else '🔴 Waiting...'}</div>",
        unsafe_allow_html=True)

st.markdown("<hr style='border-color:#21262d;margin:0 0 12px 0'>", unsafe_allow_html=True)

if cleaned:
    if rhythm == "normal":
        st.markdown('<div class="normal-banner">✓ &nbsp; NORMAL SINUS RHYTHM &nbsp; · &nbsp; CLEANED SIGNAL</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="afib-banner">⚠ &nbsp; ATRIAL FIBRILLATION &nbsp; · &nbsp; CLEANED SIGNAL</div>',
                    unsafe_allow_html=True)
else:
    st.info("Waiting for data — make sure main.py and stage2.py are both running.")

# HRV metrics
st.markdown('<div class="section-label">HRV metrics</div>', unsafe_allow_html=True)
m1,m2,m3,m4,m5,m6 = st.columns(6)
with m1: st.metric("Heart rate",  f"{hrv.get('mean_hr',0):.1f} bpm")
with m2: st.metric("SDNN",        f"{hrv.get('sdnn',0):.1f} ms")
with m3: st.metric("RMSSD",       f"{hrv.get('rmssd',0):.1f} ms")
with m4: st.metric("pNN50",       f"{hrv.get('pnn50',0):.1f}%")
with m5: st.metric("Mean RR",     f"{hrv.get('mean_rr',0):.0f} ms")
with m6: st.metric("Beats",       f"{info.get('n_beats',0)}")

if cleaned:
    q = cleaned.get("quality","good")
    qc = {"good":"#3fb950","low":"#d29922","noisy":"#f85149"}.get(q,"#8b949e")
    st.markdown(f"<div style='font-size:12px;color:{qc};margin:6px 0 2px'>● Signal quality: {q.upper()}</div>",
                unsafe_allow_html=True)

# Raw vs Cleaned
st.markdown('<div class="section-label">Raw (noisy) vs Cleaned — same window</div>',
            unsafe_allow_html=True)

col_raw, col_clean = st.columns(2)
raw_samples   = list(st.session_state.raw_buf)
clean_samples = list(st.session_state.clean_buf)
r_peaks       = cleaned.get("r_peaks", []) if cleaned else []
offset        = max(0, len(clean_samples) - ECG_DISPLAY)
peaks         = [p - offset for p in r_peaks if offset <= p < offset + ECG_DISPLAY]

with col_raw:
    st.plotly_chart(
        ecg_plot(raw_samples, [], "#444c56", title="Raw signal (before Stage 2)"),
        use_container_width=True, config={"displayModeBar": False}, key="raw_ecg")

with col_clean:
    st.plotly_chart(
        ecg_plot(clean_samples[-ECG_DISPLAY:], peaks, color,
                 title="Cleaned signal — R-peaks marked"),
        use_container_width=True, config={"displayModeBar": False}, key="clean_ecg")

# Time series charts
st.markdown('<div class="section-label">Signal history</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

with c1:
    st.plotly_chart(
        rr_plot(st.session_state.rr_hist, color, cfill),
        use_container_width=True, config={"displayModeBar": False}, key="rr_hist")

with c2:
    st.plotly_chart(
        line_plot(st.session_state.sdnn_hist, color, cfill,
                  title="SDNN over time", y_label="ms",
                  hline=50, hline_label="AFib threshold"),
        use_container_width=True, config={"displayModeBar": False}, key="sdnn_hist")

with c3:
    st.plotly_chart(
        line_plot(st.session_state.hr_hist, color, cfill,
                  title="Heart rate over time", y_label="bpm"),
        use_container_width=True, config={"displayModeBar": False}, key="hr_hist")

# JSON preview
with st.expander("📄 shared/input.json — what the neural network receives"):
    if cleaned:
        preview = {k: v for k, v in cleaned.items() if k != "clean_ecg"}
        preview["clean_ecg"] = f"[{len(cleaned.get('clean_ecg',[]))} floats — omitted for display]"
        st.json(preview)
    else:
        st.info("No data yet.")

time.sleep(3)
st.rerun()
