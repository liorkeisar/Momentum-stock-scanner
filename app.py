import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🚀 Master 200+ Stock Accumulation Scanner")

# רשימה מורחבת של 200 מניות מובילות (ניתן להוסיף עוד)
tickers = [
    "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PLTR", "SOUN", "MSTR", "COIN", 
    "JPM", "BAC", "GS", "MS", "INTC", "TSM", "ON", "QCOM", "MU", "ADI", "TXN", "NXPI", "MCHP",
    "AVGO", "CSCO", "ORCL", "CRM", "ADBE", "NFLX", "PYPL", "INTU", "ADP", "AMGN", "GILD",
    "REGN", "VRTX", "BKNG", "MDLZ", "PEP", "COST", "WMT", "TGT", "SBUX", "CAT", "DE", "HON",
    "IBM", "ORLY", "LOW", "HD", "MCD", "VZ", "T", "CMCSA", "DIS", "NFLX", "UBER", "ABNB"
]

def scan_single_stock(ticker):
    try:
        df = yf.Ticker(ticker).history(period="150d")
        if len(df) < 60: return None
        
        # בולינגר
        df['MA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Lower'] = df['MA20'] - (2 * df['STD'])
        
        # MFI
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        mf = tp * df['Volume']
        pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos / neg)))
        
        # תנאי צבירה: קרובה לבולינגר + MFI עולה + ווליום מעל ממוצע
        if df['Close'].iloc[-1] <= df['Lower'].iloc[-1] * 1.03 and mfi.iloc[-1] > mfi.iloc[-5]:
            if df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]:
                return (ticker, df, mfi.iloc[-1])
    except: return None
    return None

if st.button("סרוק את כל השוק (מקסימום מניות)"):
    with st.spinner("סורק נתונים..."):
        # הרצה מקבילית להאצת התהליך
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(scan_single_stock, tickers))
        
        found_stocks = [r for r in results if r is not None]
        
    if found_stocks:
        st.success(f"מצאתי {len(found_stocks)} הזדמנויות!")
        for ticker, df, mfi_val in found_stocks:
            with st.expander(f"מניה מאותרת: {ticker} (MFI: {round(mfi_val, 1)})"):
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers', 
                                         marker=dict(symbol='triangle-up', size=15, color='green')))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("לא נמצאו מניות כרגע. נסה שוב בשלב מאוחר יותר של יום המסחר.")
