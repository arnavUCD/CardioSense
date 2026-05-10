"""
dashboard.py — reads latest_result.json, writes rhythm choice to mode.txt.
"""

import json
import time
import os
from collections import deque

import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="ECG Monitor", page_icon="🫀",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  .stApp { background-color: #0d1117; color: #e6edf3; }
  section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }
  div[data-testid="metric-container"] {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 12px; padding: 16px 20px;
  }
  div[data-testid="metric-container"] label {
    color: #8b949e !important; font-size: 12px !important;
    letter-spacing: 0.08em; text-transform: uppercase;
  }
  div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-size: 28px !important; font-weight: 500 !important;
  }
  .afib-alert {
    background:#3d1f1f; border:1px solid #f85149; border-radius:10px;
    padding:10px 18px; color:#f85149; font-weight:500; font-size:15px;
    text-align:center; margin-bottom:8px;
  }
  .normal-status {
    background:#1a2f1a; border:1px solid #3fb950; border-radius:10px;
    padding:10px 18px; color:#3fb950; font-weight:500; font-size:15px;
    text-align:center; margin-bottom:8px;
  }
  .other-status {
    background:#2d2a1a; border:1px solid #d29922; border-radius:10px;
    padding:10px 18px; color:#d29922; font-weight:500; font-size:15px;
    text-align:center; margin-bottom:8px;
  }
  .section-label {
    color:#8b949e; font-size:11px; letter-spacing:0.1em;
    text-transform:uppercase; margin-bottom:6px; margin-top:20px;
  }
  /* Sidebar rhythm toggle styling */
  div[data-testid="stRadio"] label {
    font-size: 14px !important;
    color: #e6edf3 !important;
  }
  /* Sidebar is always visible — hide all collapse/expand controls */
  button[data-testid="collapsedControl"],
  button[data-testid="baseButton-headerNoPadding"] { display: none !important; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

BASE        = os.path.dirname(__file__)
RESULT_FILE = os.path.join(BASE, "latest_result.json")
MODE_FILE   = os.path.join(BASE, "mode.txt")
ECG_DISPLAY_SAMPLES = 750

# ── Sidebar — rhythm selector ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Signal control")
    st.markdown("---")
    st.markdown("**Rhythm mode**")
    st.markdown("<div style='font-size:12px;color:#8b949e;margin-bottom:12px'>Choose what signal the pipeline generates</div>",
                unsafe_allow_html=True)

    rhythm = st.radio(
        label="rhythm_select",
        options=["Normal sinus", "AFib (arrhythmia)"],
        index=0,
        label_visibility="collapsed",
    )

    rhythm_key = "normal" if rhythm == "Normal sinus" else "afib"

    # Write chosen rhythm to file so main.py picks it up
    with open(MODE_FILE, "w") as f:
        f.write(rhythm_key)

    st.markdown("---")

    # Visual indicator
    if rhythm_key == "normal":
        st.markdown("""
        <div style='background:#1a2f1a;border:1px solid #3fb950;border-radius:8px;
                    padding:10px 14px;font-size:13px;color:#3fb950'>
          ● Sending normal sinus rhythm
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:#3d1f1f;border:1px solid #f85149;border-radius:8px;
                    padding:10px 14px;font-size:13px;color:#f85149'>
          ⚠ Sending AFib signal
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='font-size:11px;color:#8b949e;margin-top:16px'>Changes take effect within 3 seconds</div>",
                unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "ecg_buffer" not in st.session_state:
    st.session_state.ecg_buffer = deque(maxlen=ECG_DISPLAY_SAMPLES)

# ── Read latest result ────────────────────────────────────────────────────────
latest = None
connected = False
if os.path.exists(RESULT_FILE):
    try:
        with open(RESULT_FILE) as f:
            latest = json.load(f)
        connected = True
        st.session_state.ecg_buffer.extend(
            latest.get("clean_ecg", [])[-ECG_DISPLAY_SAMPLES:]
        )
    except Exception:
        pass

# ── Helpers ───────────────────────────────────────────────────────────────────
def cls_color(cls):
    return {"Normal": "#3fb950", "AFib": "#f85149", "Other": "#d29922"}.get(cls, "#8b949e")

def banner(cls, conf):
    css   = {"Normal":"normal-status","AFib":"afib-alert","Other":"other-status"}
    icons = {"Normal":"✓","AFib":"⚠","Other":"~"}
    st.markdown(
        f'<div class="{css.get(cls,"other-status")}">'
        f'{icons.get(cls,"?")}  {cls.upper()}  ·  {conf*100:.0f}% confidence</div>',
        unsafe_allow_html=True)

def ecg_fig(samples, r_peaks, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(len(samples))), y=samples,
        mode="lines", line=dict(color=color, width=1.2), hoverinfo="skip"))
    valid = [p for p in r_peaks if 0 <= p < len(samples)]
    if valid:
        fig.add_trace(go.Scatter(x=valid, y=[samples[p] for p in valid],
            mode="markers",
            marker=dict(color="#f0883e", size=6, symbol="triangle-down"),
            hoverinfo="skip"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
        margin=dict(l=8,r=8,t=8,b=8), height=180, showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="#21262d", gridwidth=0.5,
                   zeroline=True, zerolinecolor="#21262d", showticklabels=False))
    return fig

def prob_fig(probs):
    labels = list(probs.keys())
    values = [probs[l]*100 for l in labels]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=[cls_color(l) for l in labels], marker_line_width=0,
        text=[f"{v:.0f}%" for v in values], textposition="outside",
        textfont=dict(color="#8b949e", size=12), cliponaxis=False))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8,r=48,t=8,b=8), height=110, showlegend=False,
        xaxis=dict(range=[0,110], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(color="#8b949e", size=12)),
        bargap=0.4)
    return fig

# ── Main layout ───────────────────────────────────────────────────────────────
c1, c2 = st.columns([5,1])
with c1:
    st.markdown("## Stage 1 — ECG Arrhythmia Monitor")
with c2:
    st.markdown(
        f"<div style='text-align:right;padding-top:20px;font-size:13px;color:#8b949e'>"
        f"{'🟢 Live' if connected else '🔴 Waiting...'}</div>",
        unsafe_allow_html=True)

st.markdown("<hr style='border-color:#21262d;margin:0 0 16px 0'>", unsafe_allow_html=True)

if latest:
    banner(latest["classification"], latest["confidence"])
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Heart rate", f"{latest.get('bpm',0):.0f} bpm")
    with m2:
        rr_std = latest.get("rr_std", 0)
        st.metric("Rhythm regularity", "Irregular" if rr_std > 80 else "Regular",
                  delta=f"RR std {rr_std:.0f} ms",
                  delta_color="inverse" if rr_std > 80 else "normal")
    with m3: st.metric("Confidence", f"{latest['confidence']*100:.0f}%")
    with m4: st.metric("Signal quality", latest.get("quality","good").capitalize())
else:
    st.info("Waiting for pipeline — make sure main.py is running.")

st.markdown('<div class="section-label">Live ECG waveform</div>', unsafe_allow_html=True)
samples = list(st.session_state.ecg_buffer)
r_peaks = latest.get("r_peaks", []) if latest else []
color   = cls_color(latest["classification"]) if latest else "#58a6ff"

if samples:
    offset  = max(0, len(samples) - ECG_DISPLAY_SAMPLES)
    display = samples[-ECG_DISPLAY_SAMPLES:]
    peaks   = [p - offset for p in r_peaks if offset <= p < offset + ECG_DISPLAY_SAMPLES]
    st.plotly_chart(ecg_fig(display, peaks, color),
                    use_container_width=True, config={"displayModeBar": False})
else:
    st.markdown("<div style='height:180px;background:#161b22;border-radius:10px;'></div>",
                unsafe_allow_html=True)

cp, ci = st.columns([2,1])
with cp:
    st.markdown('<div class="section-label">Class probabilities</div>', unsafe_allow_html=True)
    if latest and latest.get("probabilities"):
        st.plotly_chart(prob_fig(latest["probabilities"]),
                        use_container_width=True, config={"displayModeBar": False})
with ci:
    st.markdown('<div class="section-label">About this window</div>', unsafe_allow_html=True)
    if latest:
        rr = latest.get("rr_intervals", [])
        mean_rr = sum(rr)/len(rr) if rr else 0
        st.markdown(f"""
        <div style='font-size:13px;color:#8b949e;line-height:2.0'>
          Window &nbsp;<span style='color:#e6edf3'>10 s · 2500 samples</span><br>
          Beats &nbsp;<span style='color:#e6edf3'>{len(latest.get("r_peaks",[]))}</span><br>
          Mean RR &nbsp;<span style='color:#e6edf3'>{mean_rr:.0f} ms</span><br>
          Rate &nbsp;<span style='color:#e6edf3'>250 Hz</span><br>
          Rhythm &nbsp;<span style='color:#e6edf3'>{rhythm}</span>
        </div>""", unsafe_allow_html=True)

time.sleep(3)
st.rerun()
