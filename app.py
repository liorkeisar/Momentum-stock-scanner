import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

# --- טעינה יציבה מקובץ ---
@st.cache_data
def get_universe():
    try:
        # טעינת הקובץ שהורדת
        df = pd.read_csv("nasdaq_screener.csv")
        # ניקוי סימולים (הסרת מניות עם בעיות)
        tickers = df['Symbol'].dropna().unique().tolist()
        return [t for t in tickers if len(t) < 6 and t.isalpha()]
    except:
        st.error("לא נמצא קובץ nasdaq_screener.csv. אנא וודא שהורדת אותו לאותה תיקייה.")
        return []

# --- לוגיקה ---
def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252 or df['Volume'].iloc[-1] < 500000: return None
        
        # אינדיקטורים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['MFI'] = 100 - (100 / (1 + (df['Volume'] * ((df['High']+df['Low']+df['Close'])/3)).rolling(14).mean()))
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        if (df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10 and 
            df['MFI'].iloc[-1] > 45 and df['RVOL'].iloc[-1] > 1.5 and 
            df['MACD'].iloc[-1] > df['Signal'].iloc[-1]):
            return ticker, df
    except: return None
    return None

# --- ממשק ---
st.title("🛡️ TITAN: File-Based Scanner")
if st.button("🚀 הפעל סריקה"):
    tickers = get_universe()
    if tickers:
        progress_bar = st.progress(0)
        results = {}
        with ThreadPoolExecutor(max_workers=50) as ex:
            futures = {ex.submit(run_scanner, t): t for t in tickers}
            for i, future in enumerate(futures):
                res = future.result()
                if res: results[res[0]] = res[1]
                progress_bar.progress((i + 1) / len(tickers))
        st.session_state['results'] = results

if 'results' in st.session_state:
    st.success(f"נמצאו {len(st.session_state['results'])} מניות!")
