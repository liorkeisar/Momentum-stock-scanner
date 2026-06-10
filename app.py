import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="Institutional Scanner Pro", layout="wide")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- פונקציות חישוב (הכוללות את כל הלוגיקה המלאה) ---
def calculate_indicators(df):
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    mf = typical * df['Volume']
    pos = mf.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg = mf.where(typical < typical.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos / neg)))
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    price_low = df['Close'].rolling(20).min()
    macd_low = df['MACD'].rolling(20).min()
    df['Divergence'] = (df['Close'] <= price_low) & (df['MACD'] > macd_low)
    return df

@st.cache_data
def get_market_data():
    return yf.Ticker("SPY").history(period="1y")['Close']

# --- Session State ---
if 'results_cache' not in st.session_state: st.session_state['results_cache'] = {}
if 'found_stocks' not in st.session_state: st.session_state['found_stocks'] = []

# --- מבנה Dashboard ---
st.title("🛡️ Institutional Accumulation Dashboard")
col_left, col_right = st.columns([1, 3])

with col_left:
    st.subheader("⚙️ בקרת סריקה")
    manual_ticker = st.text_input("מניה לבדיקה ידנית:")
    available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    index_option = st.selectbox("בחר קובץ סריקה:", available_files)
    
    if st.button('🚀 הרץ סריקה'):
        with st.status("מנתח שוק...", expanded=True) as status:
            found = []
            market_data = get_market_data()
            ticker_list = [manual_ticker.upper()] if manual_ticker else pd.read_csv(index_option, header=None)[0].dropna().tolist()
            
            for ticker in ticker_list:
                try:
                    df = yf.Ticker(ticker).history(period="1y")
                    if len(df) < 60: continue
                    df = calculate_indicators(df)
                    last = df.iloc[-1]
                    rs_score = (last['Close'] / df['Close'].iloc[-20]) / (market_data.iloc[-1] / market_data.iloc[-20])
                    
                    if (last['Divergence'] and last['MFI'] > 50 and last['RSI'] < 65 and rs_score > 1.0):
                        found.append(ticker)
                        st.session_state['results_cache'][ticker] = df
                except: continue
            
            st.session_state['found_stocks'] = found
            if not manual_ticker:
                with open('latest_results.json', 'w') as f:
                    json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "stocks": found}, f)
            status.update(label="הסריקה הושלמה!", state="complete", expanded=False)

    if st.session_state['found_stocks']:
        st.metric("נמצאו", len(st.session_state['found_stocks']))
        selected = st.selectbox("בחר מניה:", st.session_state['found_stocks'])
        st.session_state['selected'] = selected

with col_right:
    tab1, tab2 = st.tabs(["📉 גרף איסוף", "📁 סריקה שמורה"])
    with tab1:
        if 'selected' in st.session_state and st.session_state['selected'] in st.session_state['results_cache']:
            df = st.session_state['results_cache'][st.session_state['selected']]
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'))
            fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Low'].iloc[-1] * 0.98], mode='markers', marker=dict(symbol='triangle-up', size=20, color='lime'), name='אות קניה'))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
    with tab2:
        if os.path.exists('latest_results.json'):
            with open('latest_results.json', 'r') as f:
                saved = json.load(f)
                st.write(f"תאריך: {saved['date']} | מניות: {', '.join(saved['stocks'])}")
