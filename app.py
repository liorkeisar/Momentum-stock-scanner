import streamlit as st
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA"]

def check_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="5d") # רק 5 ימים, הכי מהיר שיש
        if not df.empty:
            return {'Ticker': ticker, 'Status': 'OK', 'LastPrice': round(df['Close'].iloc[-1], 2)}
        return {'Ticker': ticker, 'Status': 'Empty Data'}
    except Exception as e:
        return {'Ticker': ticker, 'Status': f'Error: {str(e)[:10]}'}

st.title("🔍 בדיקת תקינות נתונים")

if st.button("בדוק את 20 המניות הראשונות"):
    universe = get_universe()[:20]
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(check_ticker, universe))
    st.dataframe(pd.DataFrame(results))
