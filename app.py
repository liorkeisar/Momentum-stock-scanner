import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

# הגדרת דף (חייבת להיות אחרי ה-import)
st.set_page_config(layout="wide", page_title="Quantum Terminal")

# --- CSS עיצוב ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: sans-serif; }
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 20px; margin-bottom: 20px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 15px; height: 100%; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; margin-top: 8px; }
    .badge-reversal { background-color: rgba(0, 184, 135, 0.15); color: #00B887; }
    .indicator-box { margin-top: 15px; padding-top: 10px; border-top: 1px solid #1F2538; }
    .indicator-name { color: #938AA9; font-size: 0.8rem; }
    .indicator-desc { color: #5C5374; font-size: 0.7rem; display: block; margin-top: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- לוגיקה ---
def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['High20'] = df['High'].rolling(20).max().shift(1)
    df['RSI'] = 50 # דוגמה לערך
    df['MFI'] = 50 # דוגמה לערך
    return df

# --- ממשק ---
st.title("Quantum Terminal")
ticker = st.text_input("הזן סימול:", value="NVDA").upper()

if ticker:
    df = calculate_indicators(yf.Ticker(ticker).history(period="100d"))
    c1, c2 = st.columns([1, 3])
    
    with c1:
        st.markdown(f"""
        <div class="info-panel">
            <span class="ticker-symbol">{ticker}</span>
            <span class="badge badge-reversal">Reversal</span>
            <div style="font-size: 1.6rem; font-weight: 700; color: #00B887; margin-top: 10px;">${df['Close'].iloc[-1]:.2f}</div>
            <div class="indicator-box">
                <div class="indicator-name">RSI</div>
                <span class="indicator-desc">חוזק יחסי. מעל 70 קניית יתר.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)
