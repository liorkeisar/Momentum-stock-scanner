import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Market Accumulation Scanner")

# הוספתי לשונית Penny Stocks
indices = {
    "S&P 500 (Tech)": ["AAPL", "MSFT", "NVDA", "AMD", "GOOGL", "META", "ADBE", "ORCL", "CRM", "AVGO"],
    "Nasdaq 100 (Growth)": ["TSLA", "PLTR", "COIN", "MSTR", "SOUN", "MARA", "RIOT", "CLSK", "AFRM", "HOOD"],
    "Small Caps (Volatile)": ["ASST", "BBAI", "IONQ", "RIVN", "LCID", "QS", "PATH", "STEM", "JOBY", "UPST"],
    "Penny Stocks": ["FCEL", "PLUG", "TLRY", "SNDL", "BBBY", "AMC", "MULN", "FSR", "WISH", "NIO"]
}

tabs = st.tabs(list(indices.keys()))

def scan_market(tickers):
    results = []
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="60d")
            if len(df) < 30: continue
            
            # חישוב MFI
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            mf = tp * df['Volume']
            pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
            neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
            mfi = 100 - (100 / (1 + (pos / neg)))
            
            # תנאי איסוף סחורה: מחיר יורד + MFI עולה
            # שיניתי לטווח של 15 יום כדי להיות רגישים יותר ב-Penny Stocks
            if df['Close'].iloc[-1] < df['Close'].iloc[-15] and mfi.iloc[-1] > mfi.iloc[-15]:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "MFI": round(mfi.iloc[-1], 1),
                    "Status": "איסוף סחורה 🔋"
                })
        except: continue
    return pd.DataFrame(results)

for i, (name, tickers) in enumerate(indices.items()):
    with tabs[i]:
        if st.button(f"סרוק מניות ב-{name}"):
            with st.spinner(f"סורק את {name}..."):
                df = scan_market(tickers)
                if not df.empty:
                    st.dataframe(df.sort_values(by="MFI", ascending=False), use_container_width=True)
                else:
                    st.info("לא נמצאו מניות העונות לקריטריונים של איסוף סחורה במדד זה.")

st.sidebar.markdown("### טיפ למסחר:")
st.sidebar.write("במניות פני (Penny Stocks), תנועות המניה חדות יותר. חפש MFI עולה בחוזקה כסימן מוביל להיפוך.")
