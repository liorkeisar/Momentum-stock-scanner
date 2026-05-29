import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Ultimate Penny Stock Accumulation Scanner")

# חלוקה לקטגוריות מחיר (רשימות מייצגות)
penny_indices = {
    "Under $1": ["FCEL", "SNDL", "WISH", "MULN", "FSR"],
    "$1 - $5": ["PLUG", "TLRY", "AMC", "NIO", "JOBY"],
    "$5 +": ["ASST", "BBAI", "IONQ", "RIVN", "LCID"]
}

tabs = st.tabs(list(penny_indices.keys()))

def scan_penny_market(tickers):
    results = []
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="60d")
            if len(df) < 30: continue
            
            # MFI
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            mf = tp * df['Volume']
            pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
            neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
            mfi = 100 - (100 / (1 + (pos / neg)))
            
            # בדיקת איסוף: מחיר יורד בטווח קצר, MFI עולה
            if df['Close'].iloc[-1] < df['Close'].iloc[-15] and mfi.iloc[-1] > mfi.iloc[-15]:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "MFI": round(mfi.iloc[-1], 1)
                })
        except: continue
    return pd.DataFrame(results)

# לולאה ליצירת הלשוניות
for i, (name, tickers) in enumerate(penny_indices.items()):
    with tabs[i]:
        if st.button(f"סרוק מניות בטווח {name}"):
            with st.spinner("סורק..."):
                df = scan_penny_market(tickers)
                if not df.empty:
                    st.dataframe(df.sort_values(by="MFI", ascending=False), use_container_width=True)
                else:
                    st.info(f"לא נמצאו מניות באיסוף בטווח {name}.")

st.sidebar.info("הסורק מזהה סטייה בין מחיר יורד ל-MFI עולה - סימן מובהק לאיסוף סחורה.")
