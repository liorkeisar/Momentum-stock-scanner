import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🏹 Ultimate S&P 500 Trading Dashboard")

# פונקציה למשיכת רשימת הטיקרים (S&P 500)
@st.cache_data
def get_sp500_tickers():
    # רשימה בסיסית ומורחבת לביצועים מהירים ויציבות
    return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", 
            "GS", "AVGO", "INTC", "NFLX", "CRM", "ADBE", "MS", "BAC", "WMT", "COST", "DIS", 
            "HD", "V", "MA", "PFE", "JNJ", "UNH", "XOM", "CVX", "MCD", "CAT", "DE", "IBM"]

def plot_chart(df, ticker, signal_type):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='green'), name=signal_type))
    st.plotly_chart(fig, use_container_width=True)

tabs = st.tabs(["🚀 פריצות (Breakout)", "📈 סווינג", "💎 טווח ארוך"])

# פונקציות סריקה ממוקדות
def run_scan(ticker, strategy):
    df = yf.Ticker(ticker).history(period="200d")
    if len(df) < 20: return None
    
    if strategy == "breakout":
        high_20 = df['High'].rolling(20).max().iloc[-1]
        avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
        if df['Close'].iloc[-1] >= high_20 * 0.95 and df['Volume'].iloc[-1] < avg_vol:
            return df
    elif strategy == "swing":
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        lower = ma20 - (2 * df['Close'].rolling(20).std().iloc[-1])
        if df['Close'].iloc[-1] <= lower * 1.03:
            return df
    elif strategy == "long":
        if df['Close'].iloc[-1] > df['Close'].rolling(200).mean().iloc[-1]:
            return df
    return None

tickers = get_sp500_tickers()

with tabs[0]:
    if st.button("סרוק פריצות (כל המניות)"):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda t: (t, run_scan(t, "breakout")), tickers))
        for t, df in results:
            if df is not None:
                with st.expander(f"מניה בלחץ: {t}"):
                    plot_chart(df, t, "Pre-Breakout")

with tabs[1]:
    if st.button("סרוק סווינג (כל המניות)"):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda t: (t, run_scan(t, "swing")), tickers))
        for t, df in results:
            if df is not None:
                with st.expander(f"מניית סווינג (איסוף): {t}"):
                    plot_chart(df, t, "Bollinger Buy")

with tabs[2]:
    if st.button("סרוק מגמה ארוכה (כל המניות)"):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda t: (t, run_scan(t, "long")), tickers))
        for t, df in results:
            if df is not None:
                with st.expander(f"מניית מגמה חיובית: {t}"):
                    plot_chart(df, t, "Trend Follow")
