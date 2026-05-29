import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Algo-Scanner")

# הגדרה רחבה יותר של מניות כדי להגדיל סיכוי למצוא תנועה
big_caps = ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "AAPL", "AVGO", "TSM", "LLY", "NFLX", "ORCL"]
small_caps = ["SOUN", "BBAI", "CLSK", "WULF", "CIFR", "IONQ", "PLTR", "HOOD", "AFRM", "SOFI", "RIVN", "LCID"]
high_alpha = ["MSTR", "COIN", "MARA", "RIOT", "FSLR", "NVAX", "CRSP", "EDIT", "BEAM", "NTLA", "PLTR", "ARM"]

def get_signal(ticker):
    try:
        df = yf.download(ticker, period="30d", progress=False)
        if df.empty or 'Close' not in df.columns: return None
        
        # תנאי ליברלי: מניה שנסחרת מעל ממוצע 10 ימים ועלתה היום
        price_now = float(df['Close'].iloc[-1])
        price_yesterday = float(df['Close'].iloc[-2])
        sma10 = float(df['Close'].rolling(10).mean().iloc[-1])
        
        if price_now > sma10 and price_now > price_yesterday:
            change = ((price_now - price_yesterday) / price_yesterday) * 100
            return {"Ticker": ticker, "Price": round(price_now, 2), "Change %": round(change, 2)}
    except: return None
    return None

st.title("🏹 Pro Momentum Scanner (Active Market)")
t1, t2, t3 = st.tabs(["Big Caps", "Small Caps", "High Alpha"])

for tab, stocks in zip([t1, t2, t3], [big_caps, small_caps, high_alpha]):
    with tab:
        found = [res for t in stocks if (res := get_signal(t))]
        if found:
            st.dataframe(pd.DataFrame(found), use_container_width=True)
        else:
            st.warning("לא נמצאו מניות בתנועה כרגע - נסה לרענן את הדף (F5).")
