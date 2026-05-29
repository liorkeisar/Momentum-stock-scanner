import streamlit as st
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🏹 Multi-Strategy Trading Dashboard")

tickers = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", "GS", "AVGO", "INTC"]

def get_data(ticker):
    return yf.Ticker(ticker).history(period="200d")

# 1. לוגיקת מומנטום
def is_momentum(df):
    return df['Close'].iloc[-1] >= df['High'].rolling(20).max() * 0.98 and \
           df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.5

# 2. לוגיקת סווינג (איסוף בבולינגר)
def is_swing(df):
    ma20 = df['Close'].rolling(20).mean()
    lower = ma20 - (2 * df['Close'].rolling(20).std())
    return df['Close'].iloc[-1] <= lower.iloc[-1] * 1.03

# 3. לוגיקת טווח ארוך (מגמת עלייה)
def is_long_term(df):
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
