import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Long-Term Accumulation Scanner (30-Day Trend)")

# רשימה מורחבת של מניות מובילות ותנודתיות
tickers = ["NVDA", "PLTR", "SOUN", "MSTR", "COIN", "ASST", "MARA", "RIOT", "CLSK", "TSLA", "AAPL", "MSFT", "AMD"]

def get_smart_money_data(ticker):
    try:
        # הגדלנו ל-90 יום כדי שיהיה מספיק נתונים לחישוב 30 יום של מגמה
        df = yf.Ticker(ticker).history(period="90d")
        if len(df) < 60: return None
        
        # חישוב MFI (Money Flow Index)
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        positive_mf = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
        negative_mf = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + (positive_mf / negative_mf)))
        
        # חישוב ADX (עוצמת מגמה)
        plus_dm = (df['High'] - df['High'].shift(1)).clip(lower=0)
        minus_dm = (df['Low'].shift(1) - df['Low']).clip(lower=0)
        tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        adx = 100 * (abs(plus_dm - minus_dm) / (plus_dm + minus_dm)).rolling(14).mean()

        # תנאי חדש: MFI ו-ADX גבוהים יותר מאשר לפני 30 יום
        if mfi.iloc[-1] > mfi.iloc[-30] and adx.iloc[-1] > adx.iloc[-30]:
            return {
                "Ticker": ticker,
                "Price": round(df['Close'].iloc[-1], 2),
                "MFI_30d_Trend": "עולה ⬆️",
                "ADX_30d_Trend": "מתחזק ⬆️"
            }
        return None
    except: return None

if st.button("סרוק מניות בצבירה (30 יום)"):
    results = [get_smart_money_data(t) for t in tickers]
    df = pd.DataFrame([r for r in results if r is not None])
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success("המניות הללו נמצאות במגמת צבירה חיובית בחודש האחרון.")
    else:
        st.info("לא נמצאו מניות שעונות לקריטריון הצבירה ב-30 הימים האחרונים. נסה שוב מחר.")
