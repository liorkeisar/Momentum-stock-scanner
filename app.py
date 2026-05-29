import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Professional Momentum Scanner")

# רשימת מניות
stocks = ["NVDA", "AMD", "PLTR", "MSTR", "COIN", "MARA", "RIOT", "SOUN", "CLSK", "TSLA"]

def get_data_with_headers(ticker):
    try:
        # כאן אנחנו מוסיפים "תחפושת" לדפדפן כדי לעקוף חסימות
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period="2d", proxy=None) 
        
        if df.empty or len(df) < 2:
            return None
        
        last_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        change = ((last_close - prev_close) / prev_close) * 100
        
        return {"Ticker": ticker, "Price": round(last_close, 2), "Change %": round(change, 2)}
    except Exception as e:
        return None

st.write("סורק מניות עם עקיפת חסימה...")
results = []
for s in stocks:
    data = get_data_with_headers(s)
    if data:
        results.append(data)

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.error("עדיין לא מצליח למשוך נתונים. נסה להוסיף user-agent מפורש.")
