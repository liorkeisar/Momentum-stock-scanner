import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import os

st.set_page_config(page_title="Institutional Scanner Pro", layout="wide")

# --- 1. מנוע חישובים ---
def calculate_all(df, market_df):
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Divergence'] = (df['Close'] <= df['Close'].rolling(20).min()) & (df['MACD'] > df['MACD'].rolling(20).min())
    df['Is_Spike'] = df['Volume'] > (df['Volume'].rolling(20).mean() * 2)
    df['RS'] = (df['Close'] / df['Close'].iloc[0]) / (market_df['Close'] / market_df['Close'].iloc[0])
    return df

# --- 2. ממשק משתמש ---
st.title("🛡️ Institutional Accumulation Scanner")
col1, col2 = st.columns([1, 4])

with col1:
    # בחירת קובץ סריקה
    available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    index_option = st.selectbox("בחר רשימת מניות (CSV):", available_files)
    
    if st.button("🚀 הרץ סריקה על כל הרשימה"):
        st.session_state['results'] = {}
        tickers = pd.read_csv(index_option, header=None)[0].tolist()
        market_df = yf.Ticker("SPY").history(period="1y")
        
        progress = st.progress(0)
        for i, ticker in enumerate(tickers):
            progress.progress((i + 1) / len(tickers))
            try:
                df = yf.Ticker(ticker.strip()).history(period="1y")
                if len(df) > 50:
                    df = calculate_all(df, market_df.iloc[-len(df):])
                    if df.iloc[-1]['Divergence'] and df.iloc[-1]['Close'] > df.iloc[-1]['VWAP']:
                        st.session_state['results'][ticker] = df
            except: continue
        st.success("הסריקה הסתיימה!")

    if 'results' in st.session_state and st.session_state['results']:
        selected_ticker = st.selectbox("בחר מניה מהתוצאות:", list(st.session_state['results'].keys()))
        st.session_state['selected'] = selected_ticker
        
        # אינדיקטורים בצד
        df = st.session_state['results'][selected_ticker]
        last = df.iloc[-1]
        indicators = {"Divergence": last['Divergence'], "Price > VWAP": last['Close'] > last['VWAP'], 
                      "RS > 1.0": last['RS'] > 1.0, "RSI < 65": last['RSI'] < 65, "Volume Spike": last['Is_Spike']}
        for name, status in indicators.items():
            st.markdown(f"<span style='color: {'green' if status else 'red'}'>● {name}</span>", unsafe_allow_html=True)

with col2:
    if 'selected' in st.session_state:
        df = st.session_state['results'][st.session_state['selected']]
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name='VWAP', line=dict(color='yellow')))
        if all([df.iloc[-1]['Divergence'], df.iloc[-1]['Close'] > df.iloc[-1]['VWAP']]):
            fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Low'].iloc[-1]*0.98], mode='markers', 
                                    marker=dict(symbol='triangle-up', size=20, color='lime'), name='אות קניה'))
        fig.update_layout(template="plotly_dark", height=600)
        st.plotly_chart(fig, use_container_width=True)
