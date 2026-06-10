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

# --- פונקציות חישוב ---
def calculate_indicators(df):
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    # MFI
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    mf = typical * df['Volume']
    pos = mf.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg = mf.where(typical < typical.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos / neg)))
    # Bollinger & Averages
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    return df

def calculate_macd_divergence(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    price_low = df['Close'].rolling(20).min()
    macd_low = df['MACD'].rolling(20).min()
    df['Divergence'] = (df['Close'] <= price_low) & (df['MACD'] > macd_low)
    return df

@st.cache_data
def get_market_data():
    return yf.Ticker("SPY").history(period="1y")['Close']

# --- אתחול Session State ---
if 'results_cache' not in st.session_state: st.session_state['results_cache'] = {}
if 'found_stocks' not in st.session_state: st.session_state['found_stocks'] = []

# --- תפריט צדדי ---
manual_ticker = st.sidebar.text_input("הכנס מניה לבדיקה ידנית:")
available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
index_option = st.sidebar.selectbox("או בחר קובץ סריקה:", available_files)

if st.sidebar.button('🚀 הרץ סריקה'):
    found = []
    market_data = get_market_data()
    ticker_list = [manual_ticker.upper()] if manual_ticker else pd.read_csv(index_option, header=None)[0].dropna().tolist()
    
    progress_bar = st.progress(0)
    for i, ticker in enumerate(ticker_list):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if len(df) < 60: continue
            df = calculate_indicators(df)
            df = calculate_macd_divergence(df) # הוספת פונקציית הסטייה
            last = df.iloc[-1]
            
            if (last['Divergence'] and last['MFI'] > 50 and last['RSI'] < 60):
                found.append(ticker)
                st.session_state['results_cache'][ticker] = df
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    st.session_state['found_stocks'] = found
    st.success(f"נמצאו {len(found)} מניות!")

# --- תצוגה ---
if 'found_stocks' in st.session_state and st.session_state['found_stocks']:
    selected = st.selectbox("בחר מניה:", st.session_state['found_stocks'])
    if selected in st.session_state['results_cache']:
        df = st.session_state['results_cache'][selected]
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', yaxis='y2'))
        st.plotly_chart(fig, use_container_width=True)
