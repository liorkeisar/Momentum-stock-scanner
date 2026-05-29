import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 15-Day Accumulation Scanner")

# חלוקה לקטגוריות מחיר
penny_indices = {
    "Under $1": ["FCEL", "SNDL", "WISH", "MULN", "FSR", "GNS", "BBIG", "TRKA"],
    "$1 - $5": ["PLUG", "TLRY", "AMC", "NIO", "JOBY", "VERV", "KOSS"],
    "$5 +": ["ASST", "BBAI", "IONQ", "RIVN", "LCID", "QS", "PATH", "STEM"]
}

tabs = st.tabs(list(penny_indices.items()))

def scan_penny_market(tickers):
    results = []
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="60d")
            if len(df) < 30: continue
            
            # MFI 15 יום
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            mf = tp * df['Volume']
            pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
            neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
            mfi = 100 - (100 / (1 + (pos / neg)))
            
            # ווליום: ממוצע 5 ימים אחרונים מול ממוצע 15 יום
            avg_vol_short = df['Volume'].rolling(5).mean().iloc[-1]
            avg_vol_long = df['Volume'].rolling(15).mean().iloc[-1]
            vol_spike = avg_vol_short > avg_vol_long * 1.15 # עלייה של 15%
            
            # תנאי 15 יום: מחיר ירד ב-15 יום האחרונים, MFI עלה ב-15 יום האחרונים
            if df['Close'].iloc[-1] < df['Close'].iloc[-15] and mfi.iloc[-1] > mfi.iloc[-15] and vol_spike:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "MFI_15d": round(mfi.iloc[-1], 1),
                    "Vol_Trend": "High ⚡"
                })
        except: continue
    return pd.DataFrame(results)

for i, (name, tickers) in enumerate(penny_indices.items()):
    with tabs[i]:
        if st.button(f"סרוק מניות ב-{name} (15 יום)"):
            with st.spinner("סורק בטווח 15 יום..."):
                df = scan_penny_market(tickers)
                if not df.empty:
                    st.dataframe(df.sort_values(by="MFI_15d", ascending=False), use_container_width=True)
                else:
                    st.info(f"לא נמצאו מניות באיסוף בטווח 15 יום עבור {name}.")
