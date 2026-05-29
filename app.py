import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Market Accumulation Dashboard")

tickers = ["NVDA", "PLTR", "SOUN", "MSTR", "COIN", "ASST", "MARA", "RIOT", "CLSK", "TSLA", "AAPL", "MSFT", "AMD", "META", "GOOGL"]

def get_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 60: return None
        
        # MFI
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        pos_mf = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
        neg_mf = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos_mf / neg_mf)))
        
        # ADX
        plus_dm = (df['High'] - df['High'].shift(1)).clip(lower=0)
        minus_dm = (df['Low'].shift(1) - df['Low']).clip(lower=0)
        tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
        adx = 100 * (abs(plus_dm - minus_dm) / (plus_dm + minus_dm)).rolling(14).mean()
        
        return {
            "Ticker": ticker,
            "Price": round(df['Close'].iloc[-1], 2),
            "MFI": round(mfi.iloc[-1], 1),
            "ADX": round(adx.iloc[-1], 1)
        }
    except: return None

if st.button("טען את כל הנתונים"):
    results = [get_data(t) for t in tickers]
    df = pd.DataFrame([r for r in results if r is not None])
    
    # מיון לפי MFI - ככל שהוא גבוה יותר, יש יותר "זרימת כסף"
    st.dataframe(df.sort_values(by="MFI", ascending=False), use_container_width=True)
    st.write("טיפ: מניות עם MFI מעל 60 ו-ADX מתפתח נחשבות למעניינות במיוחד.")
