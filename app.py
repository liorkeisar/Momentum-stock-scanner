import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os

st.set_page_config(page_title="Institutional Scanner Pro", layout="wide")

# --- פונקציות ---
def calculate_indicators(df, market_data):
    # VWAP
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    
    # אינדיקטורים
    df['Vol_Avg_20'] = df['Volume'].rolling(20).mean()
    df['Is_Spike'] = df['Volume'] > (df['Vol_Avg_20'] * 2)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    price_low = df['Close'].rolling(20).min()
    macd_low = df['MACD'].rolling(20).min()
    df['Divergence'] = (df['Close'] <= price_low) & (df['MACD'] > macd_low)
    
    df['RS'] = (df['Close'] / df['Close'].iloc[0]) / (market_data / market_data.iloc[0])
    return df

# --- ממשק ---
st.title("🛡️ Institutional Accumulation Dashboard")
col_left, col_right = st.columns([1, 3])

with col_left:
    st.subheader("⚙️ סריקה")
    manual_ticker = st.text_input("מניה:")
    if st.button('🚀 הרץ סריקה'):
        if 'results_cache' not in st.session_state: st.session_state['results_cache'] = {}
        
        # לוגיקת סריקה
        try:
            df = yf.Ticker(manual_ticker.upper()).history(period="1y")
            df = calculate_indicators(df, yf.Ticker("SPY").history(period="1y")['Close'].iloc[-len(df):])
            last = df.iloc[-1]
            
            # בדיקת תנאים
            conditions = {
                "Divergence": last['Divergence'],
                "Price > VWAP": last['Close'] > last['VWAP'],
                "RS > 1.0": last['RS'] > 1.0,
                "RSI < 65": last['RSI'] < 65,
                "Volume Spike": last['Is_Spike']
            }
            
            st.session_state['results_cache'][manual_ticker.upper()] = {'df': df, 'cond': conditions}
            st.session_state['selected'] = manual_ticker.upper()
        except Exception as e: st.error("שגיאה בסריקה")

    # צד אינדיקטורים צבעוני
    if 'selected' in st.session_state:
        st.markdown("---")
        st.subheader("📋 סטטוס אינדיקטורים")
        conds = st.session_state['results_cache'][st.session_state['selected']]['cond']
        for name, val in conds.items():
            color = "green" if val else "red"
            st.markdown(f":{color}[● {name}]")

with col_right:
    if 'selected' in st.session_state:
        data = st.session_state['results_cache'][st.session_state['selected']]
        df = data['df']
        
        # גרף עם חץ קניה
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'))
        
        # חץ קניה במידה ותנאים התקיימו
        if all(data['cond'].values()):
            fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Low'].iloc[-1] * 0.98], mode='markers', 
                                    marker=dict(symbol='triangle-up', size=20, color='lime'), name='אות קניה'))
        
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
