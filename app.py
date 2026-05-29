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
data = [get_data(s) for s in stocks]
df = pd.DataFrame([d for d in data if d is not None])

# מיון מהחזקה לחלשה
df = df.sort_values(by="Change %", ascending=False)

# עיצוב הטבלה (צבעים)
def color_negative_red(val):
    color = 'red' if val < 0 else 'green'
    return f'color: {color}'

st.dataframe(df.style.applymap(color_negative_red, subset=['Change %']), use_container_width=True)

if st.button("רענן נתונים"):
    st.rerun()
