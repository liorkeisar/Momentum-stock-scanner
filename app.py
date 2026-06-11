import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Live Scanner")

@st.cache_data(ttl=86400)
def get_universe():
    urls = {
        "SP500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "NASDAQ100": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "DOW": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    }
    all_tickers = set()
    for url in urls.values():
        try:
            df = pd.read_html(url)[0]
            col = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
            all_tickers.update(df[col].tolist())
        except: continue
    return list(all_tickers)

def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252 or df['Volume'].iloc[-1] < 1000000: return None
        
        # חישובים פנימיים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['MFI'] = 100 - (100 / (1 + (df['Volume'] * ((df['High']+df['Low']+df['Close'])/3)).rolling(14).mean()))
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        if df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10 and df['MFI'].iloc[-1] > 45 and df['RVOL'].iloc[-1] > 1.5 and df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
            return ticker, df
    except: return None
    return None

# --- ממשק עם מד התקדמות ---
st.title("🚀 TITAN: Live Market Scanner")

if st.button("התחל סריקה"):
    tickers = get_universe()
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = {}
    
    with ThreadPoolExecutor(max_workers=50) as ex:
        # יצירת משימות
        future_to_ticker = {ex.submit(run_scanner, t): t for t in tickers}
        
        for i, future in enumerate(future_to_ticker):
            res = future.result()
            if res: results[res[0]] = res[1]
            
            # עדכון Progress Bar
            progress = (i + 1) / len(tickers)
            progress_bar.progress(progress)
            status_text.text(f"סורק מניות: {i+1}/{len(tickers)}...")
            
    st.session_state['results'] = results
    status_text.text("הסריקה הושלמה!")

if 'results' in st.session_state:
    st.success(f"נמצאו {len(st.session_state['results'])} מניות פוטנציאליות.")
    # הצגת תוצאות...
