import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Trading System")

# --- טעינה ---
@st.cache_data(ttl=86400)
def get_universe():
    try:
        url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
        df = pd.read_csv(url)
        tickers = df['Symbol'].dropna().unique().tolist()
        return [str(t) for t in tickers if len(str(t)) < 6 and str(t).isalpha()]
    except:
        return ["AAPL", "NVDA", "MSFT"]

# --- לוגיקה ---
def run_scanner(ticker, mode):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # לוגיקת "מציאה" (Mean Reversion)
        if mode == "מציאה":
            if df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
                return ticker, df, 100 # ציון ערך
        
        # לוגיקת "פריצה" (Breakout)
        elif mode == "פריצה":
            if df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
                score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
                return ticker, df, score
    except: return None
    return None

# --- ממשק ---
st.title("🛡️ TITAN: Multi-Strategy Scanner")
tab1, tab2 = st.tabs(["📉 מניות במחיר מציאה", "🚀 מניות לפני פריצה"])

def process_scan(mode):
    tickers = get_universe()
    progress_bar = st.progress(0)
    results = {}
    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(run_scanner, t, mode): t for t in tickers}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results[res[0]] = (res[1], res[2])
            progress_bar.progress((i + 1) / len(tickers))
    return dict(sorted(results.items(), key=lambda item: item[1][1], reverse=True))

# הרצה בלשוניות
with tab1:
    if st.button("סרוק מציאות"):
        st.session_state['res_val'] = process_scan("מציאה")
    if 'res_val' in st.session_state:
        for t, (df, s) in st.session_state['res_val'].items():
            st.write(f"מניה: {t} | מצאנו אותה במחיר נמוך!")

with tab2:
    if st.button("סרוק פריצות"):
        st.session_state['res_brk'] = process_scan("פריצה")
    if 'res_brk' in st.session_state:
        for t, (df, s) in st.session_state['res_brk'].items():
            st.write(f"מניה: {t} | ציון פריצה: {s}/100")
