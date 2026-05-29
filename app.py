import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🏹 Professional Trading Dashboard")

tickers = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", "GS", "AVGO", "INTC"]

def get_data(ticker):
    return yf.Ticker(ticker).history(period="200d")

def plot_chart(df, ticker, signal_type):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    # הוספת סימון חץ לפי האסטרטגיה
    fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='green'), name=signal_type))
    st.plotly_chart(fig, use_container_width=True)

tabs = st.tabs(["🚀 מומנטום", "📈 סווינג", "💎 טווח ארוך"])

with tabs[0]:
    st.header("סורק מומנטום")
    if st.button("סרוק מומנטום"):
        for t in tickers:
            df = get_data(t)
            # תנאי מומנטום
            if df['Close'].iloc[-1] >= df['High'].rolling(20).max().iloc[-1] * 0.98:
                with st.expander(f"מניה בפריצה: {t}"):
                    plot_chart(df, t, "Breakout")

with tabs[1]:
    st.header("סורק סווינג")
    if st.button("סרוק סווינג"):
        for t in tickers:
            df = get_data(t)
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            lower = ma20 - (2 * df['Close'].rolling(20).std().iloc[-1])
            if df['Close'].iloc[-1] <= lower * 1.03:
                with st.expander(f"מניית סווינג: {t}"):
                    plot_chart(df, t, "Bollinger Buy")

with tabs[2]:
    st.header("סורק טווח ארוך")
    if st.button("סרוק מגמה ארוכה"):
        for t in tickers:
            df = get_data(t)
            if df['Close'].iloc[-1] > df['Close'].rolling(200).mean().iloc[-1]:
                with st.expander(f"מניית מגמה: {t}"):
                    plot_chart(df, t, "Trend Follow")
