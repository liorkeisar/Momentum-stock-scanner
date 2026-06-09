import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# הגדרות עמוד
st.set_page_config(page_title="סורק פריצות מוסדי", layout="wide")

st.title("📈 סורק פריצות מוסדי")

# פונקציית אינדיקטורים
def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (std20 * 2)
    df['BB_Lower'] = df['MA20'] - (std20 * 2)
    df['BB_Width'] = ((df['BB_Upper'] - df['BB_Lower']) / df['MA20']) * 100
    df['Vol_MA20'] = df['Volume'].rolling(20).mean()
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Hist'] = (exp12 - exp26) - (exp12 - exp26).ewm(span=9, adjust=False).mean()
    return df

# פונקציית גרף נרות יפניים
def plot_interactive_chart(df, ticker):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='מחיר'))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='rgba(173, 216, 230, 0.5)', width=1), name='BB Upper'))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='rgba(173, 216, 230, 0.5)', width=1), name='BB Lower', fill='tonexty'))
    
    fig.update_layout(title=f"גרף נרות: {ticker}", template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# ממשק משתמש
ticker_input = st.text_area("הכנס סימבולים (מופרדים בפסיק)", "ZION, WVFC, WTFC, BPRN, BY, HBCP, CACC")
ticker_list = [t.strip() for t in ticker_input.split(',')]

if st.button('🚀 התחל סריקה'):
    found = []
    progress_bar = st.progress(0)
    for i, ticker in enumerate(ticker_list):
        try:
            df = yf.Ticker(ticker).history(period="60d")
            df = calculate_indicators(df)
            last, prev = df.iloc[-1], df.iloc[-2]
            
            if (last['BB_Width'] <= 9.5 and last['MACD_Hist'] > prev['MACD_Hist'] and last['Volume'] > (last['Vol_MA20'] * 1.2)):
                found.append(ticker)
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    st.session_state['found_stocks'] = found
    st.write("מניות שנמצאו:", found)

# ניתוח מניה
if 'found_stocks' in st.session_state and st.session_state['found_stocks']:
    selected = st.selectbox("בחר מניה מהתוצאות לניתוח:", st.session_state['found_stocks'])
    if selected:
        df = yf.Ticker(selected).history(period="60d")
        df = calculate_indicators(df)
        plot_interactive_chart(df, selected)
