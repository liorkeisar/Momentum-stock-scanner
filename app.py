import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 30-Day Robust Accumulation Scanner")

# הרחבנו מעט את רשימות המניות כדי לתת לסורק יותר "חומר גלם" לעבוד איתו
penny_indices = {
    "Under $1": ["FCEL", "SNDL", "WISH", "MULN", "FSR", "GNS", "BBIG", "TRKA", "HIVE", "BTBT", "OPTT", "CISS"],
    "$1 - $5": ["PLUG", "TLRY", "AMC", "NIO", "JOBY", "VERV", "KOSS", "CAN", "CLSK", "MARA", "WBA", "PTON"],
    "$5 +": ["ASST", "BBAI", "IONQ", "RIVN", "LCID", "QS", "PATH", "STEM", "SOUN", "PLTR", "ARM", "ABNB"]
}

tabs = st.tabs(list(penny_indices.items()))

def scan_penny_market(tickers):
    results = []
    for ticker in tickers:
        try:
            # הגדלנו את טווח הנתונים ל-120 יום כדי לאפשר חישובים ארוכי טווח
            df = yf.Ticker(ticker).history(period="120d")
            if len(df) < 60: continue
            
            # חישוב MFI (טווח 30 יום לצבירה)
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            mf = tp * df['Volume']
            pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
            neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
            mfi = 100 - (100 / (1 + (pos / neg)))
            
            # RSI 14 (סטנדרטי למצבי שוק)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # תנאי 30 יום: 
            # 1. מחיר יורד ב-30 יום האחרונים 
            # 2. MFI עולה ב-30 יום האחרונים
            # 3. RSI מתחת ל-55 (מניה לא "חמה" מדי)
            if df['Close'].iloc[-1] < df['Close'].iloc[-30] and mfi.iloc[-1] > mfi.iloc[-30] and rsi.iloc[-1] < 55:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "MFI_30d": round(mfi.iloc[-1], 1),
                    "RSI_14": round(rsi.iloc[-1], 1)
                })
        except: continue
    return pd.DataFrame(results)

for i, (name, tickers) in enumerate(penny_indices.items()):
    with tabs[i]:
        if st.button(f"סרוק מניות ב-{name} (30 יום)"):
            with st.spinner("סורק נתונים לטווח 30 יום..."):
                df = scan_penny_market(tickers)
                if not df.empty:
                    st.dataframe(df.sort_values(by="MFI_30d", ascending=False), use_container_width=True)
                else:
                    st.info(f"לא נמצאו מניות באיסוף בטווח 30 יום עבור {name}.")
