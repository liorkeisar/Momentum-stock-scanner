import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Narrow Squeeze Scanner (Pre-Breakout)")

markets = {
    "High Momentum": ["NVDA", "PLTR", "SOUN", "MSTR", "COIN", "MARA", "RIOT"],
    "Tech Giants": ["AAPL", "MSFT", "AMZN", "GOOGL", "META"]
}

tabs = st.tabs(list(markets.keys()))

def get_squeeze_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="60d")
        if len(df) < 22: return None
        
        # חישוב רצועות בולינגר
        sma20 = df['Close'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        
        # התכנסות (Squeeze): רצועות צרות ביחס לממוצע
        bb_width = (std20 / sma20)
        
        # Money Flow
        mfv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']) * df['Volume']
        cmf = mfv.rolling(20).sum() / df['Volume'].rolling(20).sum()
        
        # תנאי: BB_Width מתחת לממוצע של עצמו (דחוס) + CMF חיובי
        if bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1] and cmf.iloc[-1] > 0:
            return {
                "Ticker": ticker,
                "Price": round(df['Close'].iloc[-1], 2),
                "Squeeze_Score": round(bb_width.iloc[-1], 4),
                "CMF": round(cmf.iloc[-1], 2)
            }
        return None
    except: return None

for i, (market_name, tickers) in enumerate(markets.items()):
    with tabs[i]:
        if st.button(f"סרוק מניות בהתכנסות - {market_name}"):
            data = [get_squeeze_data(t) for t in tickers]
            df = pd.DataFrame([d for d in data if d is not None])
            
            if not df.empty:
                st.dataframe(df.sort_values(by="Squeeze_Score"), use_container_width=True)
            else:
                st.info("לא נמצאו מניות בדחיסה כרגע. נסה לשנות רשימה או לחכות לשינוי בשוק.")
