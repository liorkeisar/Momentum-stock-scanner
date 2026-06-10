import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import os

st.set_page_config(page_title="סורק פריצות מוסדי", layout="wide")
st.title("📈 סורק איסוף מוסדי")

@st.cache_data
def load_tickers(filename):
    try:
        df = pd.read_csv(filename, header=None)
        return df[0].dropna().tolist()
    except Exception as e:
        st.error(f"שגיאה בטעינת {filename}: {e}")
        return []

# מציאת קבצי ה-CSV
available_files = [f for f in os.listdir('.') if f.endswith('.csv') and f != 'requirements.txt']
index_option = st.sidebar.selectbox("בחר רשימת מניות:", available_files)

# חישוב אינדיקטורים כולל VWAP, MFI, RSI
def calculate_indicators(df):
    # VWAP
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # MFI
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    mf = typical_price * df['Volume']
    pos_flow = mf.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
    neg_flow = mf.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow)))
    
    # בולינגר
    df['MA20'] = df['Close'].rolling(20).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Width'] = ((df['MA20'] + (std20 * 2) - (df['MA20'] - (std20 * 2))) / df['MA20']) * 100
    
    return df

# הרצת הסריקה
if st.button('🚀 סרוק איסוף מוסדי'):
    found = []
    progress_bar = st.progress(0)
    ticker_list = load_tickers(index_option)
    
    for i, ticker in enumerate(ticker_list):
        try:
            time.sleep(0.1)
            df = yf.Ticker(ticker).history(period="1y") # נתונים לשנה עבור שפל שנתי
            if len(df) < 50: continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            min_low = df['Low'].tail(252).min()
            
            # תנאי איסוף מוסדי מדויק
            if (last['Close'] < (min_low * 1.1) and  # קרוב לשפל שנתי (בטווח 10%)
                last['Close'] > last['VWAP'] and    # מחיר מעל VWAP (כניסת כסף)
                last['BB_Width'] < 10 and           # דשדוש צר
                30 < last['RSI'] < 60 and           # לא במצב קיצון
                last['MFI'] > 40):                  # זרימת כסף בריאה
                found.append(ticker)
                st.session_state['results_cache'][ticker] = df
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    st.session_state['found_stocks'] = found
    st.success(f"נמצאו {len(found)} מניות בתהליך איסוף!")

# תצוגה
if 'found_stocks' in st.session_state:
    selected = st.selectbox("בחר מניה:", st.session_state['found_stocks'])
    if selected:
        df = st.session_state['results_cache'].get(selected)
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'))
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
