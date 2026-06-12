import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Stable Scanner")

# פונקציית עזר לחישוב RS
def get_market_data():
    try:
        return yf.Ticker("^GSPC").history(period="300d")
    except: return pd.DataFrame()

def run_scanner(ticker, mode, market_data):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252: return None
        
        curr_price = df['Close'].iloc[-1]
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        
        # חישוב RS מול השוק
        if not market_data.empty:
            stock_pct = df['Close'].pct_change(20).iloc[-1]
            market_pct = market_data['Close'].pct_change(20).iloc[-1]
            rs = round((stock_pct - market_pct) * 100, 2)
        else: rs = 0
            
        stop_loss = round(curr_price - (2 * atr), 2)
        take_profit = round(curr_price + (6 * atr), 2)
        
        # חישוב אינדיקטורים
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        rvol = (df['Volume'] / df['Volume'].rolling(20).mean()).iloc[-1]
        bb_width = (df['Close'].rolling(20).std() * 4 / ma20) * 100
        is_dropped = ((df['High'].rolling(252).max() - curr_price) / df['High'].rolling(252).max()) > 0.25
        
        score = 0
        if mode == "מציאה" and is_dropped and bb_width < 10:
            score = 100
        elif mode == "פריצה" and bb_width < 15 and rvol > 1.2:
            score = min(100, int((15 - bb_width) * 3 + (rvol * 20)))
            
        if score > 0:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'RS': rs, 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': score}
    except: return None
    return None

st.title("🛡️ TITAN: Stable Scanner")

# כפתור סריקה יחיד למניעת עומס
if st.button("סרוק שוק"):
    with st.spinner("סורק..."):
        market_data = get_market_data()
        tickers = ["AAPL", "NVDA", "MSFT", "AMD", "TSLA", "AMZN", "GOOGL", "META"] # רשימה מצומצמת ליציבות
        results = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            for t in tickers:
                res = ex.submit(run_scanner, t, "פריצה", market_data).result()
                if res: results.append(res)
        
        if results:
            st.session_state['data'] = pd.DataFrame(results)

if 'data' in st.session_state:
    st.dataframe(st.session_state['data'], use_container_width=True)
