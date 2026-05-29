import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏹 Bollinger Accumulation Scanner (Top 200)")

# כאן נכנסת רשימה של 200 המניות (דוגמה למבנה, ניתן להרחיב)
# במערכת אמיתית נשתמש בסינון לפי Market Cap ו-Volume
tickers = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PLTR", "SOUN", "MSTR", "COIN"] 

def get_analysis(ticker):
    df = yf.Ticker(ticker).history(period="120d")
    if len(df) < 60: return None
    
    # בולינגר בנדס
    df['MA20'] = df['Close'].rolling(20).mean()
    df['STD'] = df['Close'].rolling(20).std()
    df['Upper'] = df['MA20'] + (2 * df['STD'])
    df['Lower'] = df['MA20'] - (2 * df['STD'])
    
    # MFI
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    mf = tp * df['Volume']
    pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
    mfi = 100 - (100 / (1 + (pos / neg)))
    
    # תנאי: נגיעה בבולינגר תחתית + MFI עולה
    if df['Close'].iloc[-1] <= df['Lower'].iloc[-1] and mfi.iloc[-1] > mfi.iloc[-5]:
        return df, mfi.iloc[-1]
    return None

if st.button("סרוק 200 מניות בולינגר"):
    for ticker in tickers:
        data = get_analysis(ticker)
        if data:
            df, mfi_val = data
            st.subheader(f"מניה מאותרת: {ticker}")
            
            # גרף נרות יפניים עם Plotly
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            
            # הוספת סימון קנייה (חץ)
            fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], 
                                     mode='markers', marker=dict(symbol='triangle-up', size=15, color='green'),
                                     name='סיגנל קנייה'))
            
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"MFI נוכחי: {round(mfi_val, 2)}")
