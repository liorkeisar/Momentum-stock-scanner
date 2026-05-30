import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Pro Market Scanner", layout="wide")

# פונקציית משיכת מניות
@st.cache_data
def get_tickers(index):
    if index == "DJIA":
        return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", 
                "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", 
                "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
    try:
        return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    except: return ["AAPL", "MSFT"]

# מנוע הסריקה
def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().clip(lower=0).rolling(14).mean() / df['Close'].diff().clip(upper=0).abs().rolling(14).mean())))
        df['MA20'] = df['Close'].rolling(20).mean()
        
        if scan_type == "REVERSAL":
            if df['RSI'].iloc[-1] < 50 and df['RSI'].iloc[-1] > df['RSI'].iloc[-2] and df['Close'].iloc[-1] < df['MA20'].iloc[-1]:
                return ticker, df
        elif scan_type == "BREAKOUT":
            if df['Close'].iloc[-1] > df['High'].rolling(20).max().shift(1).iloc[-1] and df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.5:
                return ticker, df
    except: return None
    return None

# יצירת גרף מקצועי
def draw_chart(df, ticker):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(title=f"{ticker} - Professional Chart", height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
    return fig

# ממשק משתמש
st.title("⚡ Pro Market Scanner")
tab1, tab2, tab3, tab4 = st.tabs(["🚀 SP500 (Rev)", "🏢 Dow (Rev)", "📈 SP500 (Break)", "📊 Dow (Break)"])

def execute(index, scan_type):
    tickers = get_tickers(index)
    with st.spinner("סורק מניות..."):
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda t: run_scanner(t, scan_type), tickers))
        
        found = False
        for res in results:
            if res:
                ticker, df = res
                with st.expander(f"✅ {ticker} - לחץ להצגת גרף"):
                    st.plotly_chart(draw_chart(df, ticker), use_container_width=True)
                found = True
        if not found: st.warning("לא נמצאו תוצאות.")

with tab1:
    if st.button("סרוק SP500 להיפוך"): execute("SP500", "REVERSAL")
with tab2:
    if st.button("סרוק Dow להיפוך"): execute("DJIA", "REVERSAL")
with tab3:
    if st.button("סרוק SP500 לפריצה"): execute("SP500", "BREAKOUT")
with tab4:
    if st.button("סרוק Dow לפריצה"): execute("DJIA", "BREAKOUT")
