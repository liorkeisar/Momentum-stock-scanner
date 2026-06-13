import streamlit as st
import yfinance as yf
import pandas as pd
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
    except: return ["AAPL", "NVDA", "MSFT"]

def run_scanner(ticker):
    try:
        time.sleep(0.2) 
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="150d")
        
        # סינון בסיסי: לפחות 100 ימי נתונים ונפח מסחר סביר
        if len(df) < 100 or df['Volume'].mean() < 100000: return None
        
        curr_price = df['Close'].iloc[-1]
        df['MA20'] = df['Close'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        
        max_high = df['High'].max()
        # תנאי מציאה: ירידה של 10%+ מהשיא ותנודתיות מתונה
        if ((max_high - curr_price) / max_high) > 0.10 and df['BB_Width'].iloc[-1] < 30:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Signal': 'מציאה'}
        return None
    except: return None

st.title("🛡️ TITAN: Scanner")
if st.button("סרוק עכשיו"):
    universe = get_universe()[:300] 
    
    # שימוש ב-ThreadPoolExecutor בצורה תקינה
    with ThreadPoolExecutor(max_workers=5) as ex:
        # כאן התיקון: מריצים את הסורק ואז מנקים את ה-None בנפרד
        futures = [ex.submit(run_scanner, t) for t in universe]
        results = [f.result() for f in futures if f.result() is not None]
    
    if results:
        st.dataframe(pd.DataFrame(results))
    else:
        st.warning("לא נמצאו מניות שעומדות בקריטריונים.")
