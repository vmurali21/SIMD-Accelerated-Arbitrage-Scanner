import sys
import os
import time
import random

import streamlit as st
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────────
BUILD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "build"))
sys.path.append(BUILD_DIR)
import fast_pricer

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Options Arbitrage Scanner",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Base */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d0f14;
    border-right: 1px solid #1e2330;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] p {
    color: #8892a4 !important;
    font-size: 0.78rem;
    letter-spacing: 0.03em;
}
[data-testid="stSidebar"] h2 {
    color: #e2e8f0 !important;
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 1.5rem;
}

/* Main background */
.main .block-container {
    background: #080a0e;
    padding: 1.5rem 2rem;
}

/* Metric cards */
div[data-testid="metric-container"] {
    background: #0d0f14;
    border: 1px solid #1e2330;
    border-radius: 8px;
    padding: 1rem 1.2rem;
}
div[data-testid="metric-container"] label {
    color: #8892a4 !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e2e8f0 !important;
    font-size: 1.6rem !important;
    font-weight: 600;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}

/* Page title */
h1 {
    color: #e2e8f0 !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em;
}

/* Section headers */
h3 {
    color: #8892a4 !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-bottom: 1px solid #1e2330;
    padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2330;
    border-radius: 8px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# ── Session state initialisation ──────────────────────────────────────────────
if "pricer" not in st.session_state:
    st.session_state.pricer = fast_pricer.HestonMonteCarloPricer()
if "stream_spot" not in st.session_state:
    st.session_state.stream_spot = 100.0
if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0
if "total_paths" not in st.session_state:
    st.session_state.total_paths = 0
if "total_time_ms" not in st.session_state:
    st.session_state.total_time_ms = 0.0

# ── Sidebar: Heston parameters ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Model Parameters")
    V0    = st.slider("Initial Variance V₀",     0.01, 0.20, 0.04, 0.005, format="%.3f")
    kappa = st.slider("Mean Reversion κ",         0.5,  5.0,  2.0,  0.1)
    theta = st.slider("Long-Run Variance θ",      0.01, 0.20, 0.04, 0.005, format="%.3f")
    sigma = st.slider("Vol of Vol σ",             0.05, 0.80, 0.10, 0.01)
    rho   = st.slider("Correlation ρ",           -0.95, 0.0, -0.50, 0.01)
    r     = st.slider("Risk-Free Rate r",          0.0,  0.15, 0.05, 0.005, format="%.3f")
    T     = st.slider("Time to Expiry T (years)", 0.1,  2.0,  1.0,  0.05)

    st.markdown("## Simulation")
    num_paths = st.select_slider("Paths per Contract", [1000, 5000, 10000, 25000, 50000], value=10000)
    num_steps = st.select_slider("Time Steps",         [50, 100, 200], value=100)
    arb_threshold = st.slider("Arbitrage Threshold ($)", 0.05, 1.0, 0.10, 0.05)

    st.markdown("## Scanner")
    num_strikes = st.slider("Strikes in Chain", 10, 51, 25)
    auto_refresh = st.toggle("Live Refresh (0.5s)", value=True)

# ── Market data simulation ────────────────────────────────────────────────────
def fetch_chain(spot: float, n_strikes: int):
    spot += random.uniform(-0.5, 0.5)
    half = n_strikes // 2
    strikes = [spot - half + i for i in range(n_strikes)]
    chain = []
    for K in strikes:
        intrinsic = max(spot - K, 0.0)
        base = intrinsic + random.uniform(0.1, 5.0)
        bid = max(0.01, base - random.uniform(0.1, 0.5))
        ask = bid + random.uniform(0.05, 0.30)
        if random.random() < 0.05:             # ~5% chance of arb
            ask = max(0.01, base - random.uniform(1.0, 2.0))
        chain.append({"Strike": K, "Bid": bid, "Ask": ask})
    return spot, chain

# ── Pricing run ───────────────────────────────────────────────────────────────
def run_scan():
    params = fast_pricer.HestonParams()
    params.S0    = st.session_state.stream_spot
    params.V0    = V0
    params.r     = r
    params.kappa = kappa
    params.theta = theta
    params.sigma = sigma
    params.rho   = rho

    pricer = st.session_state.pricer
    spot, chain = fetch_chain(st.session_state.stream_spot, num_strikes)
    st.session_state.stream_spot = spot
    params.S0 = spot

    t0 = time.perf_counter()
    rows = []
    for opt in chain:
        K = opt["Strike"]
        fair = pricer.price_call_avx2(params, K, T, num_paths, num_steps)
        edge = fair - opt["Ask"]
        rows.append({
            "Strike":     K,
            "Bid":        opt["Bid"],
            "Ask":        opt["Ask"],
            "Fair Value": fair,
            "Edge":       edge,
            "Signal":     "BUY" if edge > arb_threshold else "—",
        })
    elapsed_ms = (time.perf_counter() - t0) * 1000

    st.session_state.scan_count    += 1
    st.session_state.total_paths   += len(chain) * num_paths
    st.session_state.total_time_ms += elapsed_ms

    return spot, rows, elapsed_ms

# ── Layout ────────────────────────────────────────────────────────────────────
header_col, refresh_col = st.columns([5, 1])
with header_col:
    st.markdown("## Options Arbitrage Scanner")
with refresh_col:
    manual_refresh = st.button("⟳  Scan", use_container_width=True)

spot, rows, elapsed_ms = run_scan()
df = pd.DataFrame(rows)

arb_rows = df[df["Signal"] == "BUY"]
avg_ms = (
    st.session_state.total_time_ms / st.session_state.scan_count
    if st.session_state.scan_count else 0
)

# ── Metric strip ──────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Underlying Spot",   f"${spot:.2f}")
m2.metric("Contracts Scanned", len(rows))
m3.metric("Arbitrage Signals", len(arb_rows),
          delta=f"+{len(arb_rows)}" if len(arb_rows) else None,
          delta_color="normal")
m4.metric("Scan Time",         f"{elapsed_ms:.1f} ms")
m5.metric("Paths This Session",f"{st.session_state.total_paths:,}")

st.divider()

# ── Main table ────────────────────────────────────────────────────────────────
st.markdown("### Options Chain")

def style_table(df: pd.DataFrame):
    def row_color(row):
        if row["Signal"] == "BUY":
            return ["background-color: #0a2012; color: #4ade80"] * len(row)
        return [""] * len(row)

    return (
        df.style
        .apply(row_color, axis=1)
        .format({
            "Strike":     "${:.2f}",
            "Bid":        "${:.2f}",
            "Ask":        "${:.2f}",
            "Fair Value": "${:.3f}",
            "Edge":       "${:+.3f}",
        })
        .set_properties(**{"text-align": "right"})
    )

st.dataframe(
    style_table(df),
    use_container_width=True,
    height=min(35 * len(df) + 38, 600),
    hide_index=True,
)

# ── Edge distribution sparkline ───────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### Edge Distribution (Fair Value − Ask)")
    chart_df = df[["Strike", "Edge"]].set_index("Strike")
    st.bar_chart(chart_df, color="#3b82f6", height=200)

with col_right:
    st.markdown("### Arbitrage Signals")
    if len(arb_rows):
        signal_df = arb_rows[["Strike", "Ask", "Fair Value", "Edge"]].copy()
        signal_df = signal_df.style.format({
            "Strike":     "${:.2f}",
            "Ask":        "${:.2f}",
            "Fair Value": "${:.3f}",
            "Edge":       "${:+.3f}",
        })
        st.dataframe(signal_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No signals this cycle.")

# ── Session stats ─────────────────────────────────────────────────────────────
st.divider()
st.markdown("### Session Performance")
s1, s2, s3 = st.columns(3)
s1.metric("Total Scans",             st.session_state.scan_count)
s2.metric("Avg Scan Time",           f"{avg_ms:.1f} ms")
s3.metric("Total Paths Simulated",   f"{st.session_state.total_paths:,}")

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(0.5)
    st.rerun()
