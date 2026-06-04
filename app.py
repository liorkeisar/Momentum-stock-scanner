import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# הגדרת דף רחב
st.set_page_config(layout="wide", page_title="Quantum Terminal Pro")

# עיצוב CSS פנימי לשיפור המראה
st.markdown("""
    <style>
    .metric-card { background-color: #111522; padding: 15px; border-radius: 10px; border: 1px solid #1F2538; }
    .analysis-box { background-color: #1A202C; padding: 15px; border-radius: 10px; border: 1px dashed #4A5568; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# פונקציות עזר
def get_data(ticker):
    df = yf.Ticker(ticker).history(period="60d")
    df['MA20'] = df['Close'].rolling(20).mean()
    return df

def draw_chart(df, ticker):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price')])
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='#E2B4BD', width=2)))
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=30, b=0))
    return fig

# --- ממשק ---
st.title("Quantum Terminal")

# יצירת טאבים
tab1, tab2 = st.tabs(["🔍 חיפוש מניה", "🚀 סורק שוק"])

with tab1:
    ticker = st.text_input("הזן סימול (לדוגמה: AAPL):", value="NVDA").upper()
    if ticker:
        df = get_data(ticker)
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f'<div class="metric-card"><h3>{ticker}</h3><p>מחיר: ${df["Close"].iloc[-1]:.2f}</p></div>', unsafe_allow_html=True)
            st.markdown('<div class="analysis-box"><b>ניתוח טכני:</b><br>מגמה מחושבת לפי MA20.</div>', unsafe_allow_html=True)
        with col2:
            st.plotly_chart(draw_chart(df, ticker), use_container_width=True)

with tab2:
    st.subheader("סורק שוק מהיר")
    if st.button("הפעל סריקה"):
        watchlist = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]
        for t in watchlist:
            df = get_data(t)
            # הצגה בטורים כדי לא להעמיס
            cols = st.columns(2)
            cols[0].write(f"**{t}**")
            cols[1].metric("מחיר", f"${df['Close'].iloc[-1]:.2f}")
