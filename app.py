import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Scanner")
st.title("🏹 Professional Momentum Scanner")

stocks = ["NVDA", "AMD", "PLTR", "MSTR", "COIN", "MARA", "RIOT", "SOUN", "CLSK", "TSLA"]

def get_data(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period="5d")
        if df.empty or len(df) < 2: return None
        
        last = float(df['Close'].iloc[-1])
        prev = float(df['Close'].iloc[-2])
        change = ((last - prev) / prev) * 100
        return {"Ticker": ticker, "Price": round(last, 2), "Change %": round(change, 2)}
    except: return None

# איסוף נתונים
results = []
for s in stocks:
    data = get_data(s)
    if data:
        results.append(data)

if results:
    df = pd.DataFrame(results).sort_values(by="Change %", ascending=False)
    st.dataframe(df, use_container_width=True)
else:
    st.write("לא נמצאו נתונים, נסה לרענן.")

if st.button("רענן נתונים"):
    st.rerun()
