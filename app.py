import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests_cache import CacheMixin, SQLiteCache

# מנגנון קאש משופר
class CachedLimiterSession(CacheMixin, Session): pass
session = CachedLimiterSession(limiter=None, cache_backend=SQLiteCache("yfinance.cache"))

def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT"]

def run_scanner(ticker):
    try:
        # השהייה אקראית קטנה כדי למנוע חסימה של "Too Many Requests"
        time.sleep(0.2) 
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="150d") # מספיק 150 ימים לחישובים שלך
        
        if len(df) < 100 or df['Volume'].mean() < 100000: return None
        
        curr_price = df['Close'].iloc[-1]
        df['MA20'] = df['Close'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        
        # תנאי מציאה מרווח יותר: ירידה של 10% במקום 25%, BB_Width עד 30 במקום 10
        max_high = df['High'].max()
        if ((max_high - curr_price) / max_high) > 0.10 and df['BB_Width'].iloc[-1] < 30:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'Signal': 'מציאה'}
        return None
    except: return None

st.title("🛡️ TITAN: Scanner")
if st.button("סרוק עכשיו"):
    universe = get_universe()[:300] # מתחילים עם 300 הראשונות כדי לוודא עבודה
    with ThreadPoolExecutor(max_workers=5) as ex: # הורדתי ל-5 כדי למנוע חסימות
        results = list(ex.filter(None, ex.map(run_scanner, universe)))
    
    if results:
        st.dataframe(pd.DataFrame(results))
    else:
        st.warning("לא נמצאו מניות. נסה להגדיל את כמות המניות בסריקה.")
