import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Breakout Hunter")

# --- טעינה יציבה מ-GitHub ---
@st.cache_data(ttl=86400)
def get_universe():
    try:
        url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
        df = pd.read_csv(url)
        tickers = df['Symbol'].dropna().unique().tolist()
        return [str(t) for t in tickers if len(str(t)) < 6 and str(t).isalpha()]
    except:
        return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

# --- מנוע ניקוד פריצה (Breakout Logic) ---
def calculate_breakout_score(df):
    score = 0
    # כיווץ רצועות בולינגר = דחיסה לקראת פריצה
    if df['BB_Width'].iloc[-1] < 5: score += 50
    elif df['BB_Width'].iloc[-1] < 10: score += 30
    
    # עלייה חדה בווליום = כניסת כסף מוסדי
    if df['RVOL'].iloc[-1] > 2.5: score += 30
    elif df['RVOL'].iloc[-1] > 1.5: score += 15
    
    # מומנטום מעל ממוצע
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 20
    
    return score

# --- סורק ---
def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        
        # תנאי סף לפריצה: רצועות צרות + ווליום מתחיל לעלות
        if df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
            score = calculate_breakout_score(df)
            return ticker, df, score
    except: return None
    return None

# --- ממשק ---
st.title("🏹 TITAN: Breakout Hunter")
st.write("סורק מניות שנמצאות בדחיסה (Squeeze) לפני פריצה מוסדית")

if st.button("🚀 התחל סריקת פריצות"):
    tickers = get_universe()
    progress_bar = st.progress(0)
    results = {}
    
    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(run_scanner, t): t for t in tickers}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results[res[0]] = (res[1], res[2])
            progress_bar.progress((i + 1) / len(tickers))
            
    # מיון לפי הציון הכי גבוה
    sorted_results = dict(sorted(results.items(), key=lambda item: item[1][1], reverse=True))
    st.session_state['results'] = sorted_results

if 'results' in st.session_state:
    for ticker, (df, score) in st.session_state['results'].items():
        with st.expander(f"מניה: {ticker} | ציון פריצה: {score}/100"):
            st.write(f"דחיסת רצועות (BB_Width): {df['BB_Width'].iloc[-1]:.1f} | עוצמת ווליום (RVOL): {df['RVOL'].iloc[-1]:.1f}x")
            fig = go.Figure(data=[go.Candlestick(x=df.index[-90:], open=df['Open'][-90:], 
                            high=df['High'][-90:], low=df['Low'][-90:], close=df['Close'][-90:])])
            fig.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig, use_container_width=True)
