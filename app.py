import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 30-Day Robust Accumulation Scanner")

# הגדרה מסודרת של הנתונים
indices_data = {
    "Under $1": ["FCEL", "SNDL", "WISH", "MULN", "FSR", "GNS", "BBIG", "TRKA", "HIVE", "BTBT"],
    "$1 - $5": ["PLUG", "TLRY", "AMC", "NIO", "JOBY", "VERV", "KOSS", "CAN", "CLSK", "MARA"],
    "$5 +": ["ASST", "BBAI", "IONQ", "RIVN", "LCID", "QS", "PATH", "STEM"]
}

# יצירת רשימת שמות הלשוניות בנפרד כדי למנוע את השגיאה
tab_names = list(indices_data.keys())
tabs = st.tabs(tab_names)

def scan_penny_market(tickers):
    results = []
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="120d")
            if len(df) < 60: continue
            
            # MFI 30 יום
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            mf = tp * df['Volume']
            pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
            neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
            mfi = 100 - (100 / (1 + (pos / neg)))
            
            # RSI 14
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # תנאי 30 יום: ירידת מחיר + עליית MFI + RSI מתחת ל-55
            if df['Close'].iloc[-1] < df['Close'].iloc[-30] and mfi.iloc[-1] > mfi.iloc[-30] and rsi.iloc[-1] < 55:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "MFI_30d": round(mfi.iloc[-1], 1),
                    "RSI": round(rsi.iloc[-1], 1)
                })
        except: continue
    return pd.DataFrame(results)

# לולאה בטוחה על הלשוניות
for i, tab_name in enumerate(tab_names):
    with tabs[i]:
        tickers = indices_data[tab_name]
        if st.button(f"סרוק מניות ב-{tab_name}", key=f"btn_{i}"):
            with st.spinner(f"סורק {tab_name}..."):
                df = scan_penny_market(tickers)
                if not df.empty:
                    st.dataframe(df.sort_values(by="MFI_30d", ascending=False), use_container_width=True)
                else:
                    st.info(f"לא נמצאו מניות באיסוף בטווח 30 יום עבור {tab_name}.")
