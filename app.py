import streamlit as st
import yfinance as yf
import pandas as pd

st.title("🔍 כלי אבחון למפתחים")

def diagnose_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="100d")
        if df.empty:
            return {'Ticker': ticker, 'Status': 'Empty DF'}
        
        # חישוב נתונים כדי לראות מה הבעיה
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        bb_width = (df['Close'].rolling(20).std() * 4 / ma20) * 100
        drop = ((df['High'].max() - df['Close'].iloc[-1]) / df['High'].max()) * 100
        
        return {'Ticker': ticker, 'Status': 'OK', 'Drop%': round(drop, 2), 'BB_Width': round(bb_width, 2)}
    except Exception as e:
        return {'Ticker': ticker, 'Status': f'Error: {str(e)[:10]}'}

if st.button("אבחן 10 מניות ראשונות"):
    tickers = ["A", "AA", "AAC", "AAL", "AAME", "AAOI", "AAON", "AAPL", "AAT", "AAU"]
    results = [diagnose_ticker(t) for t in tickers]
    st.dataframe(pd.DataFrame(results))
