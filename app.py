import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Terminal")

# --- CSS עיצוב ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; }
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 16px; margin-bottom: 20px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 14px; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

MARKET_DATA = {
    "NASDAQ_A": ["AAPL", "MSFT", "NVDA", "AMZN", "META"],
    "SP500_A": ["AAPL", "MSFT", "AMZN", "NVDA", "META"]
}

def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['High20'] = df['High'].rolling(20).max().shift(1)
    df['Vol20'] = df['Volume'].rolling(20).mean()
    return df

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        df = calculate_indicators(df)
        if scan_type == "REVERSAL":
            is_valid = (df['Close'].iloc[-1] > df['MA20'].iloc[-1]) & (df['Close'].iloc[-2] < df['MA20'].iloc[-2])
        else:
            is_valid = (df['Close'].iloc[-1] > df['High20'].iloc[-1]) & (df['Volume'].iloc[-1] > df['Vol20'].iloc[-1])
        return ticker, df if is_valid else None
    except: return None

def draw_chart(df, ticker):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=0, b=0))
    return fig

# --- ממשק ---
tabs = st.tabs(["🔍 חיפוש", "🚀 סורק"])

with tabs[0]:
    ticker = st.text_input("הזן סימול:", value="NVDA").upper()
    if ticker:
        df = calculate_indicators(yf.Ticker(ticker).history(period="100d"))
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f'<div class="info-panel"><div class="ticker-symbol">{ticker}</div><p>מחיר: ${df["Close"].iloc[-1]:.2f}</p></div>', unsafe_allow_html=True)
        with c2:
            st.plotly_chart(draw_chart(df, ticker), use_container_width=True)

with tabs[1]:
    mode = st.radio("אסטרטגיה:", ["REVERSAL", "BREAKOUT"], horizontal=True)
    if st.button("סרוק NASDAQ_A"):
        with st.spinner("סורק..."):
            with ThreadPoolExecutor(max_workers=5) as ex:
                results = list(ex.map(lambda t: run_scanner(t, mode), MARKET_DATA["NASDAQ_A"]))
            for res in results:
                if res:
                    st.success(f"נמצא איתות ב-{res[0]}")
