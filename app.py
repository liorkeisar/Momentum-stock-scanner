import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Total Market Scanner")

# --- מנוע משיכת רשימות דינמי ---
@st.cache_data(ttl=86400)
def get_universe():
    try:
        tables = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        return tables[0]['Symbol'].tolist()
    except:
        return ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "AMZN", "META", "GOOGL"]

# --- לוגיקה ---
def calculate_indicators(df):
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
    return df

def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="300d")
        if len(df) < 252 or df['Volume'].iloc[-1] < 1000000: return None
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        # תנאי איסוף מוסדי משולב
        if (last['is_dropped'] and 
            last['BB_Width'] < 10 and 
            last['MFI'] > 45 and 
            last['RVOL'] > 1.5 and 
            last['MACD'] > last['Signal']):
            return ticker, df
    except: return None
    return None

# --- ממשק משתמש ---
st.title("🚀 TITAN: Total Market Scanner")
st.write("מערכת סריקה אוטומטית ל-500 המניות הגדולות בארה\"ב")

if st.button("הפעל סריקה מקיפה"):
    with st.spinner("מושך נתונים וסורק שוק..."):
        tickers = get_universe()
        with ThreadPoolExecutor(max_workers=50) as ex:
            results = list(ex.map(run_scanner, tickers))
            st.session_state['results'] = {r[0]: r[1] for r in results if r is not None}

if 'results' in st.session_state:
    results = st.session_state['results']
    st.success(f"נמצאו {len(results)} מניות שעונות על התנאים המוסדיים!")
    
    for ticker, df in results.items():
        with st.expander(f"מניה: {ticker} | מחיר: ${df['Close'].iloc[-1]:.2f}"):
            fig = go.Figure(data=[go.Candlestick(x=df.index[-90:], open=df['Open'][-90:], high=df['High'][-90:], low=df['Low'][-90:], close=df['Close'][-90:])])
            fig.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"📊 RVOL: {df['RVOL'].iloc[-1]:.1f}x | MACD: חיובי")
