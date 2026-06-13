import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests_cache import CacheMixin, SQLiteCache

# ניהול זיכרון - זה קריטי ליציבות
class CachedLimiterSession(CacheMixin, Session): pass
session = CachedLimiterSession(limiter=None, cache_backend=SQLiteCache("yfinance.cache"))

st.set_page_config(layout="wide", page_title="TITAN: Balanced Scanner")

@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return []

def run_scanner(ticker, mode):
    try:
        time.sleep(0.1) 
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="300d")
        
        # סינון נזילות "משוחרר" יותר (200K במקום 500K)
        if len(df) < 200 or df['Volume'].rolling(20).mean().iloc[-1] < 200000: return None
        
        curr_price = df['Close'].iloc[-1]
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        # הורדנו את הסף ל-15% ירידה במקום 25% כדי לתפוס יותר מניות
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.15
        
        if mode == "מציאה":
            # שחררנו את ה-BB_Width ל-20 (מאפשר יותר "רעש" סביב המניה)
            if df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 20:
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': 100}
        
        elif mode == "פריצה":
            rvol = df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1]
            if rvol > 1.5: # דגש חזק יותר על כניסת כסף (נפח)
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': int(rvol * 10)}
                
    except: return None
    return None

st.title("🛡️ TITAN: Balanced Scanner")
mode = st.radio("בחר אסטרטגיה:", ["מציאה", "פריצה"], horizontal=True)

if st.button("סרוק עכשיו"):
    universe = get_universe()
    progress_bar = st.progress(0)
    results = []
    
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = [ex.submit(run_scanner, t, mode) for t in universe]
        for i, f in enumerate(futures):
            res = f.result()
            if res: results.append(res)
            progress_bar.progress((i + 1) / len(universe))
            
    if results:
        st.dataframe(pd.DataFrame(results))
    else:
        st.warning("עדיין 0 מניות. נסה לשנות את סינון הנפילה או הנפח.")
