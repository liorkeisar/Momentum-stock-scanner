import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import random

# הגדרת דף
st.set_page_config(page_title="S&P 500 Scanner", layout="wide")

# משיכת רשימת הטיקרים מוויקיפדיה
@st.cache_data
def get_sp500_tickers():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        df = pd.read_html(url)[0]
        return df['Symbol'].tolist()
    except:
        return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA"]

# פונקציית סריקה
def run_scan(ticker):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        # לוגיקה פשוטה לדוגמה: מניה מעל ממוצע 50
        if df['Close'].iloc[-1] > df['Close'].rolling(50).mean().iloc[-1]:
            return df
    except:
        return None
    return None

st.title("⚡ S&P 500 Momentum Scanner")
tickers = get_sp500_tickers()

if st.button("🚀 סרוק את כל ה-S&P 500"):
    with st.spinner("סורק נתונים... אנא המתן"):
        with ThreadPoolExecutor(max_workers=10) as executor:
            # הרצת הסריקה במקביל
            results = list(executor.map(run_scan, tickers))
            
        # הצגת תוצאות
        for i, df in enumerate(results):
            if df is not None:
                st.write(f"נמצאה הזדמנות בסימבול: {tickers[i]}")
                st.line_chart(df['Close'])
