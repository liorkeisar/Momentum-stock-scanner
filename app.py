import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 60-Day Accumulation Scanner")

tickers = ["NVDA", "PLTR", "SOUN", "MSTR", "COIN", "ASST", "MARA", "RIOT", "CLSK", "TSLA", "AAPL", "MSFT", "AMD", "META", "GOOGL"]

def get_smart_money_data(ticker):
    try:
        # לוקחים 120 יום כדי שיהיה טווח רחב לחישוב ממוצעים ל-60 יום
        df = yf.Ticker(ticker).history(period="120d")
        if len(df) < 80: return None
        
        # חישוב MFI
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        pos_mf = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
        neg_mf = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (pos_mf / neg_mf)))
        
        # חישוב ADX
        plus_dm = (df['High'] - df['High'].shift(1)).clip(lower=0)
        minus_dm = (df['Low'].shift(1) - df['Low']).clip(lower=0)
        tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
        adx = 100 * (abs(plus_dm - minus_dm) / (plus_dm + minus_dm)).rolling(14).mean()

        # תנאי חדש ורחב יותר: הערך הנוכחי גבוה מהממוצע של 60 יום האחרונים
        if mfi.iloc[-1] > mfi.rolling(60).mean().iloc[-1] and adx.iloc[-1] > adx.rolling(60).mean().iloc[-1]:
            return {
                "Ticker": ticker,
                "Price": round(df['Close'].iloc[-1], 2),
                "MFI_vs_60d": "מעל הממוצע",
                "ADX_vs_60d": "מעל הממוצע"
            }
        return None
    except: return None

if st.button("סרוק מניות במגמת צבירה (60 יום)"):
    results = [get_smart_money_data(t) for t in tickers]
    df = pd.DataFrame([r for r in results if r is not None])
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success("מצאתי מניות שהכסף זורם אליהן וחוזק המגמה שלהן גבוה מהממוצע של חודשיים האחרונים.")
    else:
        st.info("עדיין אין תוצאות. נסה להוסיף עוד מניות לרשימת ה-tickers בקוד.")
