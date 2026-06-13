import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests_cache import CacheMixin, SQLiteCache

# ניהול זיכרון לשיפור מהירות ומניעת חסימות
class CachedLimiterSession(CacheMixin, Session): pass
session = CachedLimiterSession(limiter=None, cache_backend=SQLiteCache("yfinance.cache"))

st.set_page_config(layout="wide", page_title="TITAN: Professional Scanner")

@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return []

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean().iloc[-1]

def run_scanner(ticker, mode):
    try:
        time.sleep(0.1) # השהייה קלה למניעת חסימות
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="300d")
        
        # סינון בסיסי לנזילות ונתונים
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        curr_price = df['Close'].iloc[-1]
        atr = calculate_atr(df)
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # לוגיקת האסטרטגיות שלך
        if mode == "מציאה":
            if df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'StopLoss': round(curr_price - (2 * atr), 2), 
                        'TakeProfit': round(curr_price + (6 * atr), 2), 'Score': 100}
        
        elif mode == "פריצה":
            rvol = df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1]
            if df['BB_Width'].iloc[-1] < 15 and rvol > 1.2:
                score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (rvol * 20)))
                return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Score': score}
                
    except: return None
    return None

st.title("🛡️ TITAN: Professional Scanner")
mode = st.radio("בחר אסטרטגיה:", ["מציאה", "פריצה"], horizontal=True)

if st.button("התחל סריקה מלאה"):
    universe = get_universe()
    progress_bar = st.progress(0)
    results = []
    
    # 15 עובדים במקביל, כפי שביקשת
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = [ex.submit(run_scanner, t, mode) for t in universe]
        for i, f in enumerate(futures):
            res = f.result()
            if res: results.append(res)
            progress_bar.progress((i + 1) / len(universe))
            
    if results:
        st.dataframe(pd.DataFrame(results).sort_values(by='Score', ascending=False))
    else:
        st.warning("לא נמצאו מניות שעומדות בקריטריונים הקפדניים.")
