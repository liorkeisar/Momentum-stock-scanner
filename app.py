import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Multi-Strategy Trading Dashboard")

tickers = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", "GS", "AVGO", "INTC"]

def get_data(ticker):
    # נשיגת נתונים ל-200 יום כדי למנוע חוסר נתונים ב-Rolling
    return yf.Ticker(ticker).history(period="200d")

# 1. לוגיקת מומנטום מתוקנת
def is_momentum(df):
    if len(df) < 20: return False
    # חישוב התנאים כערכים בודדים ולא כסדרות
    current_close = df['Close'].iloc[-1]
    max_high_20 = df['High'].rolling(20).max().iloc[-1]
    current_vol = df['Volume'].iloc[-1]
    avg_vol_20 = df['Volume'].rolling(20).mean().iloc[-1]
    
    return current_close >= (max_high_20 * 0.98) and current_vol > (avg_vol_20 * 1.5)

# 2. לוגיקת סווינג מתוקנת
def is_swing(df):
    if len(df) < 20: return False
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    std20 = df['Close'].rolling(20).std().iloc[-1]
    lower = ma20 - (2 * std20)
    return df['Close'].iloc[-1] <= (lower * 1.03)

# 3. לוגיקת טווח ארוך מתוקנת
def is_long_term(df):
    if len(df) < 200: return False
    sma200 = df['Close'].rolling(200).mean().iloc[-1]
    return df['Close'].iloc[-1] > sma200

tabs = st.tabs(["🚀 מומנטום", "📈 סווינג", "💎 טווח ארוך"])

with tabs[0]:
    st.header("סורק מומנטום")
    if st.button("סרוק מומנטום"):
        for t in tickers:
            df = get_data(t)
            if is_momentum(df): st.success(f"{t} נמצא בפריצה!")

with tabs[1]:
    st.header("סורק סווינג")
    if st.button("סרוק סווינג"):
        for t in tickers:
            df = get_data(t)
            if is_swing(df): st.warning(f"{t} בבולינגר תחתית (איסוף)")

with tabs[2]:
    st.header("סורק טווח ארוך")
    if st.button("סרוק מגמה ארוכה"):
        for t in tickers:
            df = get_data(t)
            if is_long_term(df): st.info(f"{t} מעל SMA 200 (מגמה חיובית)")
