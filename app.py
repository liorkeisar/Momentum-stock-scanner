import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Terminal")

# --- CSS עיצוב ---
st.markdown("""
    <style>
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 15px; margin-bottom: 20px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 15px; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    .trigger-reason-box { background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 10px; margin-top: 10px; font-size: 0.8rem; color: #A0AEC0; }
    </style>
""", unsafe_allow_html=True)

# --- פונקציות לוגיות ---
def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['High20'] = df['High'].rolling(20).max().shift(1)
    df['Volume_MA'] = df['Volume'].rolling(20).mean()
    return df

def get_trigger_reason(df, active_mode):
    last = df.iloc[-1]
    if active_mode == "REVERSAL":
        return f"מחיר סגירה (${last['Close']:.2f}) חצה את ממוצע ה-20."
    return f"פריצת שיא 20 יום ב-${last['High20']:.2f} עם ווליום חריג."

def draw_premium_chart(df, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='#E2B4BD', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='rgba(100, 100, 100, 0.5)'), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    return fig

# --- ממשק ---
tabs = st.tabs(["🔍 חיפוש ידני", "🚀 סורק שוק"])

with tabs[0]:
    ticker = st.text_input("הזן סימול:", value="NVDA").upper()
    if ticker:
        df = yf.Ticker(ticker).history(period="100d")
        if not df.empty:
            df = calculate_indicators(df)
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown(f'<div class="info-panel"><div class="ticker-symbol">{ticker}</div><div>${df["Close"].iloc[-1]:.2f}</div></div>', unsafe_allow_html=True)
            with c2:
                st.plotly_chart(draw_premium_chart(df, ticker), use_container_width=True)

with tabs[1]:
    mode = st.radio("אסטרטגיה:", ["REVERSAL", "BREAKOUT"], horizontal=True)
    if st.button("הפעל סריקה"):
        # דוגמה לסורק פשוט
        tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]
        for t in tickers:
            df = calculate_indicators(yf.Ticker(t).history(period="50d"))
            st.markdown(f'<div class="stock-container"><h4>{t}</h4></div>', unsafe_allow_html=True)
