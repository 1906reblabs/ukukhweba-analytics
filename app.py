# app.py — your Micro-Bloomberg MVP
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime

st.set_page_config(
    page_title="JSE Intelligence | Micro-Bloomberg",
    page_icon="📊",
    layout="wide"
)

st.title("JSE Intelligence Platform")
st.caption(f"SA Market Data · Updated {datetime.now().strftime('%d %b %Y %H:%M')}")

# --- Sidebar: Screener Controls ---
st.sidebar.header("Stock Screener")
max_pe     = st.sidebar.slider("Max P/E ratio", 0, 60, 25)
min_yield  = st.sidebar.slider("Min dividend yield (%)", 0.0, 10.0, 2.0)
min_mom    = st.sidebar.slider("Min 3-month momentum (%)", -30, 30, 0)
sector_filter = st.sidebar.multiselect(
    "Sector", ["Mining", "Finance", "Telecoms", "Energy", "Retail"], default=[]
)

# --- Load Data (cached every 15 min) ---
@st.cache_data(ttl=900)
def load_data():
    # In production: pull from Supabase. For MVP: CSV
    return pd.read_csv("jse_snapshot.csv")

df = load_data()

# Apply screener
filtered = df[
    (df["pe_ratio"].fillna(999) <= max_pe) &
    (df["div_yield"].fillna(0) * 100 >= min_yield) &
    (df["momentum_3m"].fillna(-999) >= min_mom)
]

# --- KPI Strip ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Stocks screened", len(filtered))
col2.metric("Avg P/E", f"{filtered['pe_ratio'].mean():.1f}x")
col3.metric("Avg Dividend Yield", f"{filtered['div_yield'].mean()*100:.1f}%")
col4.metric("Avg 3M Momentum", f"{filtered['momentum_3m'].mean():.1f}%")

st.divider()

# --- Screener Table ---
st.subheader("Screener Results")
display_cols = ["name", "ticker", "price", "pe_ratio", "pb_ratio",
                "div_yield", "momentum_3m", "market_cap"]
st.dataframe(
    filtered[display_cols].style.background_gradient(
        subset=["momentum_3m"], cmap="RdYlGn"
    ),
    use_container_width=True,
    hide_index=True
)

# --- Individual Stock Deep Dive ---
st.divider()
st.subheader("Stock Deep Dive")
selected = st.selectbox("Select a stock", df["ticker"].tolist())

if selected:
    stock = yf.Ticker(selected)
    hist = stock.history(period="1y")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist["Open"], high=hist["High"],
        low=hist["Low"], close=hist["Close"],
        name=selected
    ))
    fig.update_layout(
        title=f"{selected} — 12 Month Price Action",
        xaxis_title="Date",
        yaxis_title="Price (ZAR)",
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Weekly Report Embed (YOUR EDGE) ---
st.divider()
st.subheader("📋 Latest Weekly Intelligence Report")
st.info(
    "**[EMBED YOUR WEEKLY REPORT HERE]** — Paste your latest Substack/PDF content. "
    "This is your proprietary signal that no one else has."
)
# Later: pull from Substack RSS or uploaded PDF