import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Scanner")

# רשימה רחבה של מניות "חמות" (תנודתיות גבוהה)
watchlist = ["NVDA", "AMD", "PLTR", "SOUN", "BBAI", "CLSK", "MSTR", "COIN", "MARA", "RIOT", "HOOD", "AFRM", "RIVN", "TSLA", "META"]

def check_momentum(ticker):
    try:
        # ירידה ל-5 ימים בלבד כדי להבטיח טעינה מהירה
        df = yf.download(ticker, period="5d", progress=False)
        if df.empty or len(df) < 2: return None
        
        last_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        change = ((last_price - prev_price) / prev_price) * 100
        
        # החזרה של כל מניה שזזה מעל 0.1% - כדי לראות תוצאות מיד
        return {"Ticker": ticker, "Price": round(last_price, 2), "Change %": round(change, 2)}
    except: return None

st.title("🏹 Real-Time Momentum Scanner")

# סריקה אחת גדולה ופשוטה
found = []
with st.spinner("סורק שוק..."):
    for t in watchlist:
        res = check_momentum(t)
        if res: found.append(res)

if found:
    st.dataframe(pd.DataFrame(found).sort_values("Change %", ascending=False), use_container_width=True)
else:
    st.write("לא נמצאו נתונים, נסה לרענן.")
