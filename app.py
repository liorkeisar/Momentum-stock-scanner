import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Stable Scanner")

@st.cache_data(ttl=3600)
def get_tickers():
    # רשימה מצומצמת ואיכותית של 200 המניות הכי נזילות כדי למנוע שגיאות
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return df['Symbol'].dropna().unique().tolist()[:200]
    except: return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

def run_scanner(ticker):
    try:
        time.sleep(0.5) # השהייה קריטית למניעת חסימת IP
        stock = yf.Ticker(ticker)
        df = stock.history(period="150d")
        
        if len(df) < 100: return None
        
        curr_price = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        bb_width = (df['Close'].rolling(20).std().iloc[-1] * 4 / ma20) * 100
        
        # אסטרטגיה: התכווצות (Squeeze)
        if bb_width < 25: 
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'BB_Width': round(bb_width, 2)}
    except: return None
    return None

st.title("🛡️ TITAN: Stable Scanner")
if st.button("סרוק עכשיו (בטוח)"):
    tickers = get_tickers()
    results = []
    
    # שימוש ב-Workers מעטים מאוד למניעת חסימות
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(run_scanner, tickers))
    
    final_data = [r for r in results if r]
    
    if final_data:
        st.table(pd.DataFrame(final_data))
    else:
        st.warning("לא נמצאו נתונים. השרת של יאהו חוסם זמנית את הענן. נסה שוב בעוד 10 דקות.")
