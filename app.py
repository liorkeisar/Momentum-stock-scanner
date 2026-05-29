import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Professional Algo-Scanner")

tabs_stocks = {
    "Big Caps": ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "AAPL", "AVGO", "TSM", "LLY"],
    "Small Caps/Volatile": ["SOUN", "BBAI", "CLSK", "WULF", "CIFR", "IONQ", "PLTR", "HOOD", "AFRM", "SOFI"],
    "High Alpha": ["MSTR", "COIN", "MARA", "RIOT", "FSLR", "NVAX", "CRSP", "EDIT", "BEAM", "NTLA"]
}

def analyze_pre_breakout(ticker):
    try:
        df = yf.download(ticker, period="60d", progress=False)
        # בדיקה קריטית: האם הנתונים חזרו תקינים?
        if df is None or df.empty or 'Close' not in df.columns or 'Volume' not in df.columns:
            return None
        
        # חישוב אינדיקטורים
        sma20 = df['Close'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        width = (4 * std20) / sma20
        vol_avg = df['Volume'].rolling(20).mean()
        
        # בדיקת תנאי פריצה עם נתונים בטוחים
        if width.iloc[-1] < width.rolling(20).mean().iloc[-1] and \
           df['Volume'].iloc[-1] > vol_avg.iloc[-1] * 1.5:
            return {"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2)}
    except Exception:
        return None
    return None

st.title("🏹 Professional Pre-Breakout Scanner")
tab1, tab2, tab3 = st.tabs(["Big Caps", "Small Caps", "High Alpha"])

def process_tab(stocks):
    found = []
    with st.spinner(f"סורק {len(stocks)} מניות..."):
        for t in stocks:
            res = analyze_pre_breakout(t)
            if res: found.append(res)
    if found: st.dataframe(pd.DataFrame(found), use_container_width=True)
    else: st.info("לא נמצאו מניות במצב התכנסות כרגע.")

with tab1: process_tab(tabs_stocks["Big Caps"])
with tab2: process_tab(tabs_stocks["Small Caps"])
with tab3: process_tab(tabs_stocks["High Alpha"])
