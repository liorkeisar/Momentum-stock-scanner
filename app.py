import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏹 Ultimate 200+ Stock Accumulation Scanner")

# רשימה מורחבת של 100+ מניות מובילות (ניתן להוסיף עוד)
large_cap_tickers = [
    "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PLTR", "SOUN", "MSTR", "COIN", 
    "JPM", "BAC", "GS", "MS", "INTC", "TSM", "ON", "QCOM", "MU", "ADI", "TXN", "NXPI", "MCHP",
    "AVGO", "CSCO", "ORCL", "CRM", "ADBE", "NFLX", "PYPL", "INTU", "ADP", "AMGN", "GILD",
    "REGN", "VRTX", "BKNG", "MDLZ", "PEP", "COST", "WMT", "TGT", "SBUX", "CAT", "DE", "HON"
]

def get_analysis(ticker):
    try:
        # שימוש בנתונים ל-150 יום כדי לקבל ממוצעים יציבים
        df = yf.Ticker(ticker).history(period="150d")
        if len(df) < 60: return None
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Lower'] = df['MA20'] - (2 * df['STD'])
        
        # MFI
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        mf = tp * df['Volume']
        pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos / neg)))
        
        # סינון: קרוב לבולינגר + MFI עולה + ווליום מעל ממוצע
        if df['Close'].iloc[-1] <= df['Lower'].iloc[-1] * 1.03 and mfi.iloc[-1] > mfi.iloc[-5]:
            if df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]:
                return df, mfi.iloc[-1]
        return None
    except: return None

# ממשק משתמש
if st.button("סרוק את כל הרשימה (100+ מניות)"):
    progress_bar = st.progress(0)
    found_stocks = []
    
    for i, ticker in enumerate(large_cap_tickers):
        data = get_analysis(ticker)
        if data:
            found_stocks.append((ticker, data))
        progress_bar.progress((i + 1) / len(large_cap_tickers))
    
    if found_stocks:
        st.success(f"נמצאו {len(found_stocks)} מניות בתהליך צבירה!")
        for ticker, (df, mfi_val) in found_stocks:
            st.subheader(f"מניה מאותרת: {ticker}")
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers', 
                                     marker=dict(symbol='triangle-up', size=15, color='green'), name='קנייה'))
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"MFI: {round(mfi_val, 1)} | ווליום: גבוה מהממוצע")
    else:
        st.warning("לא נמצאו מניות בתנאי איסוף כרגע ברשימה המורחבת.")
