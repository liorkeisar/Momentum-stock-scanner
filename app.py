import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os

# הגדרות עמוד
st.set_page_config(page_title="Institutional Scanner Pro", layout="wide")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- פונקציות חישוב ---
def calculate_indicators(df, market_data):
    # VWAP
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    
    # Volume Spike Detection
    df['Vol_Avg_20'] = df['Volume'].rolling(20).mean()
    df['Is_Spike'] = df['Volume'] > (df['Vol_Avg_20'] * 2)
    
    # RSI & MFI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    mf = typical * df['Volume']
    pos = mf.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg = mf.where(typical < typical.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos / neg)))
    
    # MACD & Divergence
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    price_low = df['Close'].rolling(20).min()
    macd_low = df['MACD'].rolling(20).min()
    df['Divergence'] = (df['Close'] <= price_low) & (df['MACD'] > macd_low)
    
    # RS
    df['RS'] = (df['Close'] / df['Close'].iloc[0]) / (market_data / market_data.iloc[0])
    return df

@st.cache_data
def get_market_data():
    return yf.Ticker("SPY").history(period="1y")['Close']

def calculate_score(last, rs_score):
    score = 0
    if rs_score > 1.0: score += 1
    if last['Close'] > last['VWAP']: score += 1
    if last['Divergence']: score += 2
    if last['MFI'] > 50: score += 1
    if last['Is_Spike']: score += 1 # בונוס על ווליום
    return score

# --- ממשק משתמש ---
st.title("🛡️ Institutional Accumulation Dashboard")
col_left, col_right = st.columns([1, 3])

with col_left:
    st.subheader("⚙️ בקרת סריקה")
    manual_ticker = st.text_input("מניה לבדיקה ידנית:")
    available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    index_option = st.selectbox("בחר רשימה:", available_files)
    
    if st.button('🚀 הרץ סריקה'):
        if 'results_cache' not in st.session_state: st.session_state['results_cache'] = {}
        found = []
        market_data = get_market_data()
        ticker_list = [manual_ticker.upper()] if manual_ticker else pd.read_csv(index_option, header=None)[0].dropna().tolist()
        
        progress_bar = st.progress(0)
        for i, ticker in enumerate(ticker_list):
            progress_bar.progress((i + 1) / len(ticker_list))
            try:
                df = yf.Ticker(ticker).history(period="1y")
                if len(df) < 60: continue
                df = calculate_indicators(df, market_data.iloc[-len(df):])
                last = df.iloc[-1]
                
                # סינון סף מקצועי
                if last['Divergence'] and last['Close'] > last['VWAP']:
                    score = calculate_score(last, last['RS'])
                    found.append(ticker)
                    st.session_state['results_cache'][ticker] = {'df': df, 'score': score}
            except: continue
        st.session_state['found_stocks'] = found
        st.success(f"סריקה הסתיימה! נמצאו {len(found)} מניות.")

    if 'found_stocks' in st.session_state and st.session_state['found_stocks']:
        selected = st.selectbox("בחר מניה לניתוח:", st.session_state['found_stocks'])
        st.session_state['selected'] = selected

with col_right:
    if 'selected' in st.session_state and st.session_state['selected'] in st.session_state['results_cache']:
        data = st.session_state['results_cache'][st.session_state['selected']]
        df, score = data['df'], data['score']
        
        st.subheader(f"ציון איסוף מוסדי: {score}/6")
        if score >= 4: st.success("סיכוי גבוה לאיסוף מוסדי! ✅")
        
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'))
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("בצע סריקה כדי להתחיל.")
