import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# הגדרות עמוד
st.set_page_config(page_title="Institutional Scanner Pro", layout="wide")

# --- 1. מנוע חישובים (לוגיקה) ---
def calculate_all(df, market_df):
    # VWAP
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    # MACD + Divergence
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Divergence'] = (df['Close'] <= df['Close'].rolling(20).min()) & (df['MACD'] > df['MACD'].rolling(20).min())
    # Volume Spike
    df['Is_Spike'] = df['Volume'] > (df['Volume'].rolling(20).mean() * 2)
    # Relative Strength
    df['RS'] = (df['Close'] / df['Close'].iloc[0]) / (market_df['Close'] / market_df['Close'].iloc[0])
    return df

# --- 2. ממשק משתמש ---
st.title("🛡️ Institutional Accumulation Dashboard")
col1, col2 = st.columns([1, 4])

with col1:
    ticker = st.text_input("הכנס סימול (למשל: AAPL):").upper()
    if st.button("🚀 סרוק מניה"):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            market_df = yf.Ticker("SPY").history(period="1y")
            df = calculate_all(df, market_df)
            st.session_state['data'] = df
            st.session_state['ticker'] = ticker
        except: st.error("שגיאה בטעינת הנתונים")

    if 'data' in st.session_state:
        st.subheader("📋 אינדיקטורים")
        last = st.session_state['data'].iloc[-1]
        indicators = {
            "Divergence": last['Divergence'],
            "Price > VWAP": last['Close'] > last['VWAP'],
            "RS > 1.0": last['RS'] > 1.0,
            "RSI < 65": last['RSI'] < 65,
            "Volume Spike": last['Is_Spike']
        }
        for name, status in indicators.items():
            color = "green" if status else "red"
            st.markdown(f"<span style='color:{color}'>● {name}</span>", unsafe_allow_html=True)

with col2:
    if 'data' in st.session_state:
        df = st.session_state['data']
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name='VWAP', line=dict(color='yellow')))
        
        # חץ קניה
        last = df.iloc[-1]
        if last['Divergence'] and last['Close'] > last['VWAP']:
            fig.add_trace(go.Scatter(x=[df.index[-1]], y=[last['Low']*0.98], mode='markers', 
                                    marker=dict(symbol='triangle-up', size=20, color='lime'), name='אות קניה'))
        
        fig.update_layout(template="plotly_dark", height=600)
        st.plotly_chart(fig, use_container_width=True)
