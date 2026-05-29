import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Accumulation on Dip Scanner")

tickers = ["NVDA", "PLTR", "SOUN", "MSTR", "COIN", "ASST", "MARA", "RIOT", "CLSK", "TSLA", "AAPL", "MSFT", "AMD", "META", "GOOGL"]

def get_accumulation_on_dip(ticker):
    try:
        df = yf.Ticker(ticker).history(period="60d")
        if len(df) < 30: return None
        
        # חישוב MFI
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        mf = tp * df['Volume']
        pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos / neg)))
        
        # תנאים:
        # 1. מחיר ירד ב-10 ימים האחרונים
        # 2. MFI עלה ב-10 ימים האחרונים
        # 3. ווליום ממוצע ב-5 ימים האחרונים גבוה מהממוצע של 20 יום (עלייה בנפח)
        price_drop = df['Close'].iloc[-1] < df['Close'].iloc[-10]
        mfi_rising = mfi.iloc[-1] > mfi.iloc[-10]
        vol_increasing = df['Volume'].rolling(5).mean().iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]
        
        if price_drop and mfi_rising and vol_increasing:
            return {
                "Ticker": ticker,
                "Price": round(df['Close'].iloc[-1], 2),
                "MFI_Trend": "עולה ⬆️",
                "Volume_Trend": "מתחזק 📈"
            }
        return None
    except: return None

if st.button("סרוק מניות בירידה עם איסוף (Accumulation)"):
    results = [get_accumulation_on_dip(t) for t in tickers]
    df = pd.DataFrame([r for r in results if r is not None])
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success("מצאתי מניות במצב של 'צבירה בירידות'. בדוק את הגרף שלהן!")
    else:
        st.info("אין כרגע מניות שעונות על כל התנאים (ירידת מחיר + עליית MFI + עליה בווליום).")
