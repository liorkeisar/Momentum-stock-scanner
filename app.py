import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Professional Momentum Scanner")

# רשימת מניות
stocks = ["NVDA", "AMD", "PLTR", "MSTR", "COIN", "MARA", "RIOT", "SOUN", "CLSK", "TSLA"]

def get_data(ticker):
    try:
        # שימוש בסיסי ויציב - בלי פקודות מיושנות
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period="5d")
        
        if df.empty or len(df) < 2:
            return None
        
        last_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        change = ((last_close - prev_close) / prev_close) * 100
        
        return {"Ticker": ticker, "Price": round(last_close, 2), "Change %": round(change, 2)}
    except Exception:
        return None

st.write("סורק מניות...")

# הרצת הסריקה
results = []
for s in stocks:
    data = get_data(s)
    if data:
        results.append(data)

# הצגת תוצאות
if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.info("לא נמצאו נתונים כרגע. אם אתה רואה הודעה זו, נסה לרענן שוב.")
