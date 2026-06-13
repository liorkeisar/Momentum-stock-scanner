import streamlit as st
import yfinance as yf
import pandas as pd
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests_cache import CacheMixin, SQLiteCache

class CachedLimiterSession(CacheMixin, Session): pass
session = CachedLimiterSession(limiter=None, cache_backend=SQLiteCache("yfinance.cache"))

st.set_page_config(layout="wide", page_title="TITAN: ATR Diagnostic Scanner")

@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT"]

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="300d")
        
        # 1. בדיקת נזילות (צוואר הבקבוק המרכזי)
        if len(df) < 252: return {'Ticker': ticker, 'Status': 'נפסל: נתונים חסרים'}
        if df['Volume'].rolling(20).mean().iloc[-1] < 500000: return {'Ticker': ticker, 'Status': 'נפסל: נזילות נמוכה'}
        
        curr_price = df['Close'].iloc[-1]
        # חישוב ATR
        high_low = df['High'] - df['Low']
        atr = high_low.rolling(14).mean().iloc[-1]
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # 2. סינון לוגי לפי אסטרטגיה
        if mode == "מציאה":
            if not df['is_dropped'].iloc[-1]: return {'Ticker': ticker, 'Status': 'נפסל: לא בנפילה מספקת'}
            if df['BB_Width'].iloc[-1] >= 10: return {'Ticker': ticker, 'Status': 'נפסל: תנודתיות גבוהה מדי'}
            return {'Ticker': ticker, 'Status': 'נמצאה!', 'Price': round(curr_price, 2), 'Score': 100}
            
        return {'Ticker': ticker, 'Status': 'נפסל: לא עומד בתנאי אסטרטגיה'}
        
    except: return {'Ticker': ticker, 'Status': 'שגיאת מערכת'}

st.title("🛡️ TITAN: Diagnostic Scanner")

if st.button("סרוק עם ניתוח סיבות"):
    universe = get_universe()[:200] # הרצה על 200 הראשונות לבדיקה מהירה
    results = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(lambda t: run_scanner(t, "מציאה"), universe))
    
    # הצגת התוצאות
    df_results = pd.DataFrame(results)
    st.dataframe(df_results, use_container_width=True)
    
    # סיכום סטטיסטי
    st.subheader("סיכום סיבות פסילה:")
    st.write(df_results['Status'].value_counts())
