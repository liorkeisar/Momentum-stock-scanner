import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Market Accumulation Scanner")

# רשימות מייצגות לכל מדד (כמות מוגבלת כדי למנוע קריסה)
indices = {
    "S&P 500 (Tech)": ["AAPL", "MSFT", "NVDA", "AMD", "GOOGL", "META", "ADBE", "ORCL", "CRM", "AVGO"],
    "Nasdaq 100 (Growth)": ["TSLA", "PLTR", "COIN", "MSTR", "SOUN", "MARA", "RIOT", "CLSK", "AFRM", "HOOD"],
    "Small Caps (Volatile)": ["ASST", "BBAI", "IONQ", "RIVN", "LCID", "QS", "PATH", "STEM", "JOBY", "UPST"]
}

tabs = st.tabs(list(indices.keys()))

def scan_market(tickers):
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
            
            # תנאי צבירה: מחיר יורד + MFI עולה + ווליום במגמת עלייה
            if df['Close'].iloc[-1] < df['Close'].iloc[-10] and mfi.iloc[-1] > mfi.iloc[-10]:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "MFI": round(mfi.iloc[-1], 1)
                })
        except: continue
    return pd.DataFrame(results)

# יצירת לשוניות עם כפתור סריקה אישי לכל אחת
for i, (name, tickers) in enumerate(indices.items()):
    with tabs[i]:
        if st.button(f"סרוק מניות ב-{name}"):
            with st.spinner(f"סורק את {name}..."):
                df = scan_market(tickers)
                if not df.empty:
                    st.dataframe(df.sort_values(by="MFI", ascending=False), use_container_width=True)
                else:
                    st.info("לא נמצאו מניות העונות לקריטריונים במדד זה.")
