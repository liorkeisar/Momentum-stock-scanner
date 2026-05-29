import streamlit as st
import pandas as pd
import requests

st.title("🏹 Simple Market Scanner")

# רשימת מניות לבדיקה
tickers = ["NVDA", "AMD", "PLTR", "SOUN", "MSTR", "COIN", "TSLA", "META"]

def get_price(ticker):
    try:
        # שימוש ב-API פשוט יותר
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        prices = response['chart']['result'][0]['indicators']['quote'][0]['close']
        last = prices[-1]
        prev = prices[-2]
        change = ((last - prev) / prev) * 100
        return {"Ticker": ticker, "Price": round(last, 2), "Change %": round(change, 2)}
    except:
        return None

st.write("סורק מניות...")
data = [get_price(t) for t in tickers]
data = [d for d in data if d is not None]

if data:
    st.dataframe(pd.DataFrame(data), use_container_width=True)
else:
    st.error("לא ניתן למשוך נתונים. ייתכן שאתה חסום עקב מגבלות IP של הענן.")
