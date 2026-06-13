import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(layout="wide", page_title="TITAN: Bulletproof Scanner")

st.title("🛡️ TITAN: Scanner")

# פונקציית בדיקה בטוחה
def fetch_data(ticker):
    try:
        # עבודה ללא Cache מורכב כדי למנוע נעילות
        stock = yf.Ticker(ticker)
        df = stock.history(period="50d") # תקופה קצרה למניעת עומס
        if df.empty: return None
        
        # חישוב בסיסי
        last_price = df['Close'].iloc[-1]
        vol = df['Volume'].mean()
        if vol < 100000: return None # סינון נזילות בסיסי
        
        return {'Ticker': ticker, 'Price': round(last_price, 2), 'Volume': int(vol)}
    except:
        return None

# רשימת מניות לדוגמה כדי לוודא שזה עובד
if st.button("התחל סריקה בטוחה"):
    tickers = ["AAPL", "NVDA", "MSFT", "AMD", "TSLA", "META", "GOOGL", "AMZN", "NFLX", "INTC"]
    
    results = []
    progress_bar = st.progress(0)
    
    # הצגת טבלה מתעדכנת
    table_placeholder = st.empty()
    
    for i, ticker in enumerate(tickers):
        res = fetch_data(ticker)
        if res:
            results.append(res)
            # עדכון טבלה בזמן אמת
            table_placeholder.table(pd.DataFrame(results))
        
        progress_bar.progress((i + 1) / len(tickers))
        time.sleep(0.5) # השהייה ארוכה למניעת חסימה מוחלטת
