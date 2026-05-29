import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Pre-Breakout Squeeze Scanner")

# הגדרת שווקים
markets = {
    "Blue Chips": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"],
    "Volatility": ["PLTR", "SOUN", "MSTR", "COIN", "MARA", "RIOT", "CLSK", "TSLA"]
}

tabs = st.tabs(list(markets.keys()))

def get_squeeze_score(ticker):
    try:
        df = yf.Ticker(ticker).history(period="30d")
        if len(df) < 20: return None
        
        # חישוב רצועות בולינגר (לזיהוי התכנסות)
        sma = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        bb_width = (std / sma) * 100 # ככל שנמוך יותר = התכנסות
        
        # חישוב Money Flow פשוט (לפי נפח ומחיר)
        mfv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']) * df['Volume']
        cmf = mfv.rolling(20).sum() / df['Volume'].rolling(20).sum()
        
        return {
            "Ticker": ticker,
            "Price": round(df['Close'].iloc[-1], 2),
            "BB_Width": round(bb_width.iloc[-1], 2),
            "CMF": round(cmf.iloc[-1], 3)
        }
    except: return None

# לולאה על הלשוניות
for i, (market_name, tickers) in enumerate(markets.items()):
    with tabs[i]:
        if st.button(f"סרוק {market_name}"):
            data_list = [get_squeeze_score(t) for t in tickers]
            df = pd.DataFrame([d for d in data_list if d is not None])
            
            # סינון: BB_Width נמוך (התכנסות) ו-CMF עולה/חיובי
            df = df.sort_values(by="BB_Width")
            st.dataframe(df, use_container_width=True)
            st.write("הסבר: BB_Width נמוך מעיד על התכנסות. CMF חיובי מעיד על כניסת כסף.")
