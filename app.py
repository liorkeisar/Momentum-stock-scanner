import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests_cache
from concurrent.futures import ThreadPoolExecutor

# הגדרת מטמון עם User-Agent כדי להיראות כמו דפדפן כרום אמיתי
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

st.set_page_config(layout="wide", page_title="TITAN: Bulletproof Scanner")

def fetch_data(ticker):
    try:
        # פנייה מבוקרת עם Session המוגדר כדפדפן
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="150d")
        
        if df.empty or len(df) < 100: return None
        
        # חישוב התכווצות (Bollinger Squeeze)
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        std20 = df['Close'].rolling(20).std().iloc[-1]
        bb_width = (std20 * 4 / ma20) * 100
        
        # סינון: רק מניות בהתכווצות (BB_Width < 20)
        if bb_width < 20:
            return {'Ticker': ticker, 'Price': round(df['Close'].iloc[-1], 2), 'BB_Width': round(bb_width, 2)}
        return None
    except:
        return None

st.title("🛡️ TITAN: Bulletproof Scanner")

if st.button("סרוק עכשיו (עם מנגנון עקיפת חסימות)"):
    # רשימה מצומצמת לבדיקה
    tickers = ["AAPL", "NVDA", "MSFT", "AMD", "TSLA", "META", "GOOGL", "AMZN", "NFLX", "INTC"]
    
    results = []
    progress = st.progress(0)
    
    for i, t in enumerate(tickers):
        res = fetch_data(t)
        if res: results.append(res)
        progress.progress((i + 1) / len(tickers))
        time.sleep(0.5) # השהייה קריטית למניעת חסימה
    
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.error("השרת עדיין חסום. הדרך היחידה להמשיך היא להריץ את הקוד הזה על המחשב האישי שלך.")
