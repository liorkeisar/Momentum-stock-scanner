import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Professional Momentum Scanner")

# רשימה ממוקדת של 10 מניות חמות בלבד
stocks = ["NVDA", "AMD", "PLTR", "MSTR", "COIN", "MARA", "RIOT", "SOUN", "CLSK", "TSLA"]

def get_simple_data(ticker):
    try:
        # הורדה של 2 ימים בלבד כדי להבטיח מהירות מקסימלית
        df = yf.download(ticker, period="2d", progress=False)
        
        # בדיקת תקינות בסיסית ביותר
        if df.empty or len(df) < 2:
            return None
        
        # חישוב שינוי יומי (פשוט)
        last_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        change = ((last_close - prev_close) / prev_close) * 100
        
        return {"Ticker": ticker, "Price": round(last_close, 2), "Change %": round(change, 2)}
    except Exception:
        return None

# הצגת נתונים בטבלה
st.write("סורק נתונים...")
results = []
for s in stocks:
    data = get_simple_data(s)
    if data:
        results.append(data)

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.write("לא נמצאו מניות כרגע. נסה לרענן את הדף (F5).")
