import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Professional Algo-Scanner")

tabs_stocks = {
    "Big Caps": ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "AAPL", "AVGO", "TSM", "LLY"],
    "Small Caps/Volatile": ["SOUN", "BBAI", "CLSK", "WULF", "CIFR", "IONQ", "PLTR", "HOOD", "AFRM", "SOFI"],
    "High Alpha": ["MSTR", "COIN", "MARA", "RIOT", "FSLR", "NVAX", "CRSP", "EDIT", "BEAM", "NTLA"]
}

def analyze_pre_breakout(ticker):
    try:
        df = yf.download(ticker, period="60d", progress=False)
        if df.empty or len(df) < 30: return None
        
        # --- תיקון ה-KeyError הקריטי ---
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # --------------------------------
        
        # חישוב בולינגר
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Width'] = (4 * df['STD']) / df['SMA20']
        
        if df['Width'].isnull().iloc[-1]: return None
        
        # לוגיקת צבירה (Accumulation)
        is_tight = df['Width'].iloc[-1] < df['Width'].rolling(20).mean().iloc[-1]
        is_vol_flow = df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.5
        
        if is_tight and is_vol_flow:
            return {"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2)}
    except Exception:
        return None
    return None

st.title("🏹 Professional Pre-Breakout Scanner")
tab1, tab2, tab3 = st.tabs(["Big Caps", "Small Caps", "High Alpha"])

def process_tab(stocks):
    found = []
    with st.spinner("סורק מניות..."):
        for t in stocks:
            res = analyze_pre_breakout(t)
            if res: found.append(res)
    if found: st.dataframe(pd.DataFrame(found), use_container_width=True)
    else: st.info("לא נמצאו איתותי התכנסות כרגע.")

with tab1: process_tab(tabs_stocks["Big Caps"])
with tab2: process_tab(tabs_stocks["Small Caps"])
with tab3: process_tab(tabs_stocks["High Alpha"])
