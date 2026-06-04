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
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 15px; margin-bottom: 20px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 15px; }
    .ticker-symbol { font-size: 1.5rem; font-weight: 700; color: #FFFFFF; }
    .trigger-reason-box { background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 10px; margin-top: 10px; font-size: 0.8rem; color: #A0AEC0; }
    </style>
""", unsafe_allow_html=True)

def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['High20'] = df['High'].rolling(20).max().shift(1)
    df['Vol20'] = df['Volume'].rolling(20).mean()
    df['RSI'] = 100 - (100 / (1 + df['Close'].diff().clip(lower=0).rolling(14).mean() / (-df['Close'].diff().clip(upper=0).rolling(14).mean())))
    return df

def get_trigger_reason(df, active_mode):
    last = df.iloc[-1]
    if active_mode == "REVERSAL":
        return f"מחיר ${last['Close']:.2f} חצה את ממוצע ה-20."
    return f"פריצת שיא 20 יום ב-${last['High20']:.2f} עם ווליום גבוה."

def draw_premium_chart(df, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='#E2B4BD')), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume'), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10))
    return fig

def render_info_panel(ticker, df, active_mode, price_color):
    last = df.iloc[-1]
    reason = get_trigger_reason(df, active_mode)
    html = f"""
    <div class="info-panel">
        <div class="ticker-symbol">{ticker}</div>
        <div style="color: {price_color}; font-size: 1.2rem;">${last['Close']:.2f}</div>
        <div class="trigger-reason-box"><b>🔍 Analysis:</b><br>{reason}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- לוגיקה ראשית ---
ticker_input = st.text_input("הזן סימול (למשל: NVDA):").upper()

if ticker_input:
    df = yf.Ticker(ticker_input).history(period="100d")
    if not df.empty:
        df = calculate_indicators(df)
        
        # יצירת העמודות לפני הניסיון להציג בהן
        col1, col2 = st.columns([1, 3])
        
        with col1:
            render_info_panel(ticker_input, df, "REVERSAL", "#00B887")
            
        with col2:
            st.plotly_chart(draw_premium_chart(df, ticker_input), use_container_width=True)
    else:
        st.error("לא נמצאו נתונים.")
