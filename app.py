import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Algo-Scanner")

# רשימות מניות
big_caps = ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "AAPL", "AVGO", "TSM", "LLY"]
small_caps = ["SOUN", "BBAI", "CLSK", "WULF", "CIFR", "IONQ", "PLTR", "HOOD", "AFRM", "SOFI"]
high_alpha = ["MSTR", "COIN", "MARA", "RIOT", "FSLR", "NVAX", "CRSP", "EDIT", "BEAM", "NTLA"]

def get_signal(ticker):
    try:
        df = yf.download(ticker, period="60d", progress=False)
        if df.empty or 'Close' not in df.columns or 'Volume' not in df.columns: return None
        
        # חישובים פשוטים וישירים
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Width'] = (4 * df['STD']) / df['SMA20']
        
        # בדיקת תנאי התכנסות וזרימת כסף
        if df['Width'].iloc[-1] < df['Width'].rolling(20).mean().iloc[-1] and \
           df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.2:
            return {"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2)}
    except: return None
    return None

st.title("🏹 Professional Pre-Breakout Scanner")
t1, t2, t3 = st.tabs(["Big Caps", "Small Caps", "High Alpha"])

# סריקה נפרדת לכל טאב ללא תלות בפונקציות מורכבות
with t1:
    found = [res for t in big_caps if (res := get_signal(t))]
    st.dataframe(pd.DataFrame(found) if found else st.write("אין איתותים"), use_container_width=True)

with t2:
    found = [res for t in small_caps if (res := get_signal(t))]
    st.dataframe(pd.DataFrame(found) if found else st.write("אין איתותים"), use_container_width=True)

with t3:
    found = [res for t in high_alpha if (res := get_signal(t))]
    st.dataframe(pd.DataFrame(found) if found else st.write("אין איתותים"), use_container_width=True)
