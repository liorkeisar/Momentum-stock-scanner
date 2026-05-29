import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Accumulation & Breakout Scanner")

tickers = ["NVDA", "PLTR", "SOUN", "MSTR", "COIN", "ASST", "MARA", "RIOT", "CLSK", "TSLA"]

def get_smart_money_data(ticker):
    try:
        # דרושה היסטוריה ארוכה יותר כדי לראות את המגמה (חודשיים לפחות)
        df = yf.Ticker(ticker).history(period="60d")
        if len(df) < 30: return None
        
        # חישוב MFI (Money Flow Index)
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        positive_mf = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
        negative_mf = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (positive_mf / negative_mf)))
        
        # חישוב ADX פשוט (עוצמת מגמה)
        plus_dm = (df['High'] - df['High'].shift(1)).clip(lower=0)
        minus_dm = (df['Low'].shift(1) - df['Low']).clip(lower=0)
        tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        adx = 100 * (abs(plus_dm - minus_dm) / (plus_dm + minus_dm)).rolling(14).mean()

        # תנאי: MFI עולה (כסף נכנס) ו-ADX מתחיל לטפס (תחילת מגמה)
        if mfi.iloc[-1] > mfi.iloc[-10] and adx.iloc[-1] > adx.iloc[-10]:
            return {
                "Ticker": ticker,
                "Price": round(df['Close'].iloc[-1], 2),
                "MFI": round(mfi.iloc[-1], 2),
                "ADX": round(adx.iloc[-1], 2)
            }
        return None
    except: return None

if st.button("סרוק מניות בתהליך צבירה (Accumulation)"):
    results = [get_smart_money_data(t) for t in tickers]
    df = pd.DataFrame([r for r in results if r is not None])
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success("המניות הללו מציגות עלייה ב-MFI וב-ADX – סימן לכניסת כסף ותחילת תנועה.")
    else:
        st.info("לא נמצאו מניות שעונות על קריטריון הצבירה כרגע.")
