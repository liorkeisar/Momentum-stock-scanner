import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Total Market Scanner")

# --- טעינה ישירה מ-GitHub ---
@st.cache_data(ttl=86400)
def get_universe():
    try:
        # קישור Raw ישיר מה-GitHub שלך
        url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
        df = pd.read_csv(url)
        tickers = df['Symbol'].dropna().unique().tolist()
        # ניקוי: השארת סימולים תקינים בלבד
        return [str(t) for t in tickers if len(str(t)) < 6 and str(t).isalpha()]
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ מה-GitHub: {e}")
        return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

# --- לוגיקה ---
def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        # סינון נזילות: ווליום ממוצע מעל 500k
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        # חישוב אינדיקטורים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['MFI'] = 100 - (100 / (1 + (df['Volume'] * ((df['High']+df['Low']+df['Close'])/3)).rolling(14).mean()))
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # תנאי מוסדי
        if (df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10 and 
            df['MFI'].iloc[-1] > 45 and df['RVOL'].iloc[-1] > 1.5 and 
            df['MACD'].iloc[-1] > df['Signal'].iloc[-1]):
            return ticker, df
    except: return None
    return None

# --- ממשק ---
st.title("🛡️ TITAN: Total Market Scanner")
st.write("סריקת מניות מבוססת קובץ ה-Nasdaq שלך ב-GitHub")

if st.button("🚀 התחל סריקת שוק מלאה"):
    tickers = get_universe()
    st.write(f"סורק {len(tickers)} מניות...")
    
    progress_bar = st.progress(0)
    results = {}
    
    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(run_scanner, t): t for t in tickers}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results[res[0]] = res[1]
            progress_bar.progress((i + 1) / len(tickers))
            
    st.session_state['results'] = results

if 'results' in st.session_state:
    res = st.session_state['results']
    st.success(f"נמצאו {len(res)} מניות פוטנציאליות!")
    for ticker, df in res.items():
        with st.expander(f"מניה: {ticker}"):
            fig = go.Figure(data=[go.Candlestick(x=df.index[-90:], open=df['Open'][-90:], 
                            high=df['High'][-90:], low=df['Low'][-90:], close=df['Close'][-90:])])
            fig.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig, use_container_width=True)
