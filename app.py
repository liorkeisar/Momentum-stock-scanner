import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

# הגדרות תצוגה
st.set_page_config(layout="wide", page_title="TITAN: ATR Professional")

# טעינת רשימת המניות
@st.cache_data(ttl=86400)
def get_universe():
    filename = "nasdaq_screener.csv"
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            # לוקחים את עמודת ה-Symbol מהקובץ המקומי
            return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
        except: pass
    return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA", "AMZN", "META", "GOOGL"]

# חישוב ATR
def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean().iloc[-1]

# מנוע סריקה משופר (יציבות מקסימלית)
def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        # שימוש ב-300 ימים כפי שביקשת
        df = stock.history(period="300d")
        if len(df) < 252: return None
        
        # בדיקת ווליום יציבה
        if df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        curr_price = df['Close'].iloc[-1]
        atr = calculate_atr(df)
        
        # אינדיקטורים טכניים
        ma20 = df['Close'].rolling(20).mean()
        rvol = df['Volume'] / df['Volume'].rolling(20).mean()
        bb_width = (df['Close'].rolling(20).std() * 4 / ma20) * 100
        is_dropped = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # ניהול סיכונים
        stop_loss = round(curr_price - (2 * atr), 2)
        take_profit = round(curr_price + (6 * atr), 2)
        
        # לוגיקת סריקה
        if mode == "מציאה" and is_dropped.iloc[-1] and bb_width.iloc[-1] < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': 100}
        
        elif mode == "פריצה" and bb_width.iloc[-1] < 15 and rvol.iloc[-1] > 1.2:
            score = min(100, int((15 - bb_width.iloc[-1]) * 3 + (rvol.iloc[-1] * 20)))
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': score}
            
    except Exception:
        return None
    return None

# ממשק משתמש
st.title("🛡️ TITAN: ATR Professional Scanner")
tab1, tab2 = st.tabs(["📉 מציאות", "🚀 פריצות"])

def render_tab(mode, filename):
    if st.button(f"סרוק {mode}"):
        with st.spinner("סורק מניות ומחשב רמות ATR..."):
            universe = get_universe()
            results = []
            # שימוש ב-ThreadPoolExecutor עם מנגנון מוגן
            with ThreadPoolExecutor(max_workers=10) as ex:
                results = list(filter(None, ex.map(lambda t: run_scanner(t, mode), universe)))
            
            if results:
                df = pd.DataFrame(results).sort_values(by='Score', ascending=False)
                df.to_csv(filename, index=False)
                st.session_state[mode] = df
            else: 
                st.warning("לא נמצאו מניות בתנאים אלו.")

    if mode in st.session_state:
        st.dataframe(st.session_state[mode], use_container_width=True)
        st.download_button(f"📥 הורד אקסל {mode}", data=st.session_state[mode].to_csv(index=False), file_name=f"{mode}.csv")
        if st.button(f"🗑️ נקה {mode}", key=f"clear_{mode}"):
            if os.path.exists(filename): os.remove(filename)
            if mode in st.session_state: del st.session_state[mode]
            st.rerun()

with tab1: render_tab("מציאה", "res_val.csv")
with tab2: render_tab("פריצה", "res_brk.csv")
