import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏹 Advanced Bollinger Accumulation Scanner (Top 200)")

# רשימה מורחבת של מניות מובילות (ניתן להוסיף עוד סימולים)
tickers = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PLTR", "SOUN", "MSTR", "COIN", 
           "JPM", "BAC", "GS", "MS", "INTC", "TSM", "ON", "QCOM", "MU", "ADI", "TXN", "NXPI", "MCHP"]

def get_analysis(ticker):
    try:
        df = yf.Ticker(ticker).history(period="120d")
        if len(df) < 60: return None
        
        # חישוב בולינגר
        df['MA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Lower'] = df['MA20'] - (2 * df['STD'])
        
        # MFI
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        mf = tp * df['Volume']
        pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos / neg)))
        
        # תנאי מרוכך: מחיר בטווח של 3% מעל הבולינגר התחתון + MFI עולה
        if df['Close'].iloc[-1] <= df['Lower'].iloc[-1] * 1.03 and mfi.iloc[-1] > mfi.iloc[-5]:
            return df, mfi.iloc[-1]
        return None
    except: return None

if st.button("סרוק עכשיו"):
    found = False
    for ticker in tickers:
        data = get_analysis(ticker)
        if data:
            found = True
            df, mfi_val = data
            st.subheader(f"מניה מאותרת: {ticker}")
            
            # גרף נרות יפניים
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers', 
                                     marker=dict(symbol='triangle-up', size=15, color='green'), name='קנייה'))
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"**סטטוס:** MFI בעלייה ({round(mfi_val, 1)}), מחיר קרוב לבולינגר תחתית.")
    
    if not found:
        st.warning("לא נמצאו מניות שעומדות בתנאי הקיצון כרגע. נסה להרחיב את רשימת הטיקרים.")
