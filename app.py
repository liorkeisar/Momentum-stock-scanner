import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Core Strategies")

@st.cache_data(ttl=86400)
def get_universe():
    filename = "nasdaq_screener.csv"
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        symbols = df['Symbol'].dropna().unique().tolist()
        np.random.shuffle(symbols) 
        return [str(t) for t in symbols if len(str(t)) < 6 and str(t).isalpha()]
    return []

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # סינון בסיסי: שווי שוק מעל 500M
        if info.get('marketCap', 0) < 500_000_000: return None
        
        if mode == "ערך עמוק":
            pe = info.get('trailingPE', 0)
            if 0 < pe < 15:
                return {'Ticker': ticker, 'Price': info.get('currentPrice', 0), 'Metric': f"PE: {round(pe, 2)}"}
            return None
        
        # אסטרטגיית מציאה (טכנית)
        df = stock.history(period="1y")
        if len(df) < 200: return None
        
        # סינון: רק מניות מעל ממוצע 200
        if df['Close'].iloc[-1] < df['Close'].rolling(200).mean().iloc[-1]: return None
        
        bb_width = (df['Close'].rolling(20).std() * 4 / df['Close'].rolling(20).mean()) * 100
        if bb_width.iloc[-1] < 5:
            return {'Ticker': ticker, 'Price': round(df['Close'].iloc[-1], 2), 'Metric': 'Volatility Squeeze'}
            
    except: return None
    return None

st.title("🛡️ TITAN: Core Strategies Scanner")
mode = st.radio("בחר אסטרטגיה:", ["מציאה", "ערך עמוק"], horizontal=True)
save_file = f"results_{mode}.csv"

if st.button("התחל סריקה"):
    universe = get_universe()
    progress_bar = st.progress(0)
    with open(save_file, "w") as f: f.write("Ticker,Price,Metric\n")
        
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(run_scanner, t, mode) for t in universe]
        for i, f in enumerate(futures):
            res = f.result()
            if res:
                with open(save_file, "a") as f:
                    f.write(f"{res['Ticker']},{res['Price']},{res['Metric']}\n")
            progress_bar.progress((i + 1) / len(universe))
            
    st.success("הסריקה הסתיימה בהצלחה!")

if os.path.exists(save_file):
    st.dataframe(pd.read_csv(save_file), use_container_width=True)
