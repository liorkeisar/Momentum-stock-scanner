import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Professional Algo-Scanner")

# הגדרת רשימות מניות
tabs_stocks = {
    "Big Caps": ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "AAPL", "AVGO", "TSM", "LLY"],
    "Small Caps/Volatile": ["SOUN", "BBAI", "CLSK", "WULF", "CIFR", "IONQ", "PLTR", "HOOD", "AFRM", "SOFI"],
    "High Alpha": ["MSTR", "COIN", "MARA", "RIOT", "FSLR", "NVAX", "CRSP", "EDIT", "BEAM", "NTLA"]
}

def analyze_pre_breakout(ticker):
    df = yf.download(ticker, period="60d", progress=False)
    if len(df) < 50: return None
    
    # חישוב התכנסות (Bollinger Squeeze)
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['STD'] = df['Close'].rolling(20).std()
    df['Upper'] = df['SMA20'] + (df['STD'] * 2)
    df['Lower'] = df['SMA20'] - (df['STD'] * 2)
    df['Width'] = (df['Upper'] - df['Lower']) / df['SMA20']
    
    # בדיקת זרימת כסף: מחזור גבוה מהממוצע בזמן שהמחיר יציב
    avg_vol = df['Volume'].rolling(20).mean()
    price_range = df['High'] - df['Low']
    
    is_tight = df['Width'].iloc[-1] < df['Width'].rolling(20).mean().iloc[-1]
    is_vol_flow = df['Volume'].iloc[-1] > avg_vol.iloc[-1] * 1.5
    
    if is_tight and is_vol_flow:
        return {"Ticker": ticker, "Price": round(df['Close'].iloc[-1], 2), "Signal": "Accumulation"}
    return None

st.title("🏹 Professional Pre-Breakout Scanner")
tab1, tab2, tab3 = st.tabs(["Big Caps", "Small Caps", "High Alpha"])

def process_tab(stocks):
    found = []
    with st.spinner("סורק התכנסויות..."):
        for t in stocks:
            res = analyze_pre_breakout(t)
            if res: found.append(res)
    if found: st.dataframe(pd.DataFrame(found), use_container_width=True)
    else: st.info("לא נמצאו מניות בתהליך צבירה.")

with tab1: process_tab(tabs_stocks["Big Caps"])
with tab2: process_tab(tabs_stocks["Small Caps"])
with tab3: process_tab(tabs_stocks["High Alpha"])
