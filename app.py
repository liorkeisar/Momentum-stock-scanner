import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🏹 Professional Trading Dashboard")

tickers = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", "GS", "AVGO", "INTC", "NFLX", "CRM", "ADBE"]

def get_data(ticker):
    return yf.Ticker(ticker).history(period="200d")

def plot_chart(df, ticker, title):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='green'), name='Signal'))
    st.plotly_chart(fig, use_container_width=True)

tabs = st.tabs(["🚀 פריצות (Breakout)", "📈 סווינג", "💎 טווח ארוך"])

with tabs[0]:
    st.header("סורק פריצות (לחץ לפני מהלך)")
    if st.button("סרוק פריצות"):
        for t in tickers:
            df = get_data(t)
            # לוגיקה: מחיר ב-5% מהשיא, ווליום נמוך מהממוצע (שקט)
            high_20 = df['High'].rolling(20).max().iloc[-1]
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if df['Close'].iloc[-1] >= high_20 * 0.95 and df['Volume'].iloc[-1] < avg_vol:
                with st.expander(f"מניה בלחץ לקראת פריצה: {t}"):
                    plot_chart(df, t, "Pre-Breakout")

with tabs[1]:
    st.header("סורק סווינג")
    if st.button("סרוק סווינג"):
        for t in tickers:
            df = get_data(t)
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            lower = ma20 - (2 * df['Close'].rolling(20).std().iloc[-1])
            if df['Close'].iloc[-1] <= lower * 1.03:
                with st.expander(f"מניית סווינג (איסוף): {t}"):
                    plot_chart(df, t, "Bollinger Buy")

with tabs[2]:
    st.header("סורק טווח ארוך")
    if st.button("סרוק מגמה ארוכה"):
        for t in tickers:
            df = get_data(t)
            if df['Close'].iloc[-1] > df['Close'].rolling(200).mean().iloc[-1]:
                with st.expander(f"מניית מגמה חיובית: {t}"):
                    plot_chart(df, t, "Trend Follow")
