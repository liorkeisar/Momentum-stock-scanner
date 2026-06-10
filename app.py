import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import os
import json
from datetime import datetime

st.set_page_config(page_title="סורק איסוף מוסדי Pro", layout="wide")
st.title("🛡️ סורק איסוף מוסדי - Pro")

# --- פונקציות עזר ---
def calculate_indicators(df):
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    mf = typical * df['Volume']
    pos = mf.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg = mf.where(typical < typical.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos / neg)))
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Width'] = ((df['MA20'] + (std20 * 2) - (df['MA20'] - (std20 * 2))) / df['MA20']) * 100
    return df

@st.cache_data
def get_market_data():
    return yf.Ticker("SPY").history(period="1y")['Close']

# --- ממשק ---
if 'results_cache' not in st.session_state: st.session_state['results_cache'] = {}

st.sidebar.header("בקרת סריקה")
manual_ticker = st.sidebar.text_input("הכנס מניה לבדיקה ידנית (למשל: AAPL):")
available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
index_option = st.sidebar.selectbox("או בחר רשימת מניות מקובץ:", available_files)

# לוגיקת סריקה (ידנית או רשימה)
if st.sidebar.button('🚀 הרץ סריקה'):
    found = []
    market_data = get_market_data()
    
    # אם הוכנסה מניה ידנית, נשתמש בה. אם לא, נשתמש ברשימה מהקובץ
    ticker_list = [manual_ticker.upper()] if manual_ticker else pd.read_csv(index_option, header=None)[0].dropna().tolist()
    
    progress_bar = st.progress(0)
    for i, ticker in enumerate(ticker_list):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if len(df) < 60: continue
            df = calculate_indicators(df)
            last = df.iloc[-1]
            rs_score = (last['Close'] / df['Close'].iloc[-20]) / (market_data.iloc[-1] / market_data.iloc[-20])
            
            # תנאי איסוף
            if (last['Close'] < (df['Low'].tail(252).min() * 1.15) and 
                last['Close'] > last['MA50'] and 
                last['Close'] > (last['VWAP'] * 1.01) and
                last['BB_Width'] < 10 and 
                40 < last['RSI'] < 65 and 
                last['MFI'] > 50 and
                rs_score > 1.0):
                found.append(ticker)
                st.session_state['results_cache'][ticker] = df
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    st.session_state['found_stocks'] = found
    st.success(f"נמצאו {len(found)} מניות איכותיות!")

# --- תצוגה ---
if 'found_stocks' in st.session_state and st.session_state['found_stocks']:
    selected = st.selectbox("בחר מניה מהתוצאות:", st.session_state['found_stocks'])
    df = st.session_state['results_cache'].get(selected)
    if df is not None:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='מחיר')])
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'))
        fig.add_trace(go.Scatter(
            x=[df.index[-1]], y=[df['Low'].iloc[-1] * 0.98],
            mode='markers+text',
            marker=dict(symbol='triangle-up', size=20, color='lime'),
            name='אות קניה'
        ))
        st.plotly_chart(fig, use_container_width=True)
