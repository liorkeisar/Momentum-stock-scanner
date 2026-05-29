def get_signal(ticker):
    try:
        df = yf.download(ticker, period="60d", progress=False)
        if df.empty or 'Close' not in df.columns: return None
        
        # 1. מגמה: המחיר מעל ממוצע 20
        is_uptrend = df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1]
        
        # 2. עוצמה: מחזור מסחר חזק מהממוצע (מעיד על כסף שנכנס)
        is_strong_vol = df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.2
        
        # 3. קו זינוק: המחיר נמצא ב-10% העליונים של הטווח האחרון (Breakout Setup)
        recent_high = df['High'].rolling(20).max().iloc[-1]
        is_near_breakout = df['Close'].iloc[-1] >= (recent_high * 0.95)
        
        if is_uptrend and is_strong_vol and is_near_breakout:
            return {"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2), "Status": "Breakout Ready"}
    except: return None
    return None
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Algo-Scanner")

# רשימות מניות
big_caps = ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "AAPL", "AVGO", "TSM", "LLY"]
small_caps = ["SOUN", "BBAI", "CLSK", "WULF", "CIFR", "IONQ", "PLTR", "HOOD", "AFRM", "SOFI"]
high_alpha = ["MSTR", "COIN", "MARA", "RIOT", "FSLR", "NVAX", "CRSP", "EDIT", "BEAM", "NTLA"]

def get_signal(ticker):
    try:
        df = yf.download(ticker, period="60d", progress=False)
        if df.empty or 'Close' not in df.columns or 'Volume' not in df.columns: return None
        
        # חישוב אינדיקטורים: ממוצע 20 יום
        df['SMA20'] = df['Close'].rolling(20).mean()
        vol_avg = df['Volume'].rolling(20).mean()
        
        # תנאי פריצה משופר: 
        # 1. מחיר מעל ממוצע 20 (מגמה חיובית)
        # 2. מחזור היום גבוה מהממוצע (זרימת כסף)
        if df['Close'].iloc[-1] > df['SMA20'].iloc[-1] and \
           df['Volume'].iloc[-1] > vol_avg.iloc[-1] * 1.1: # רגישות גבוהה יותר (1.1 במקום 1.5)
            return {"Ticker": ticker, "Price": round(float(df['Close'].iloc[-1]), 2), "Vol_Spike": "Yes"}
    except: return None
    return None

st.title("🏹 Professional Pre-Breakout Scanner")
t1, t2, t3 = st.tabs(["Big Caps", "Small Caps", "High Alpha"])

for tab, stocks in zip([t1, t2, t3], [big_caps, small_caps, high_alpha]):
    with tab:
        found = [res for t in stocks if (res := get_signal(t))]
        if found:
            st.dataframe(pd.DataFrame(found), use_container_width=True)
        else:
            st.write("סורק... (אם מופיע ריק, נסה לרענן)")
