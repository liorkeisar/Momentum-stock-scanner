import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Pro Market Scanner", layout="wide")

# --- פונקציות עזר ---
@st.cache_data
def get_tickers(index):
    if index == "DJIA":
        return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", 
                "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", 
                "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
    try:
        return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    except: return ["AAPL", "MSFT"]

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

# פונקציית גרף מקצועית עם תצוגת נרות ונפח מסחר
def draw_chart(df, ticker, scan_type):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{ticker} Price', 'Volume'), 
                        row_width=[0.2, 0.7])

    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    colors = ['green' if row['Close'] >= row['Open'] else 'red' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

    fig.add_annotation(row=1, col=1, x=df.index[-1], y=df['High'].iloc[-1],
                       text=f"▲ {scan_type}", showarrow=True, arrowhead=2, 
                       arrowcolor="yellow", font=dict(color="yellow"))

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, 
                      showlegend=False, margin=dict(l=20, r=20, t=50, b=20))
    return fig

# --- ממשק ---
st.title("⚡ Pro Market Scanner")
tab1, tab2, tab3, tab4 = st.tabs(["🚀 SP500 (Rev)", "🏢 Dow (Rev)", "📈 SP500 (Break)", "📊 Dow (Break)"])

def execute(index, scan_type):
    tickers = get_tickers(index)
    with st.spinner(f"סורק {len(tickers)} מניות..."):
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda t: run_scanner(t, scan_type), tickers))
        
        found = False
        for res in results:
            if res:
                ticker, df = res
                with st.expander(f"✅ {ticker}"):
                    st.plotly_chart(draw_chart(df, ticker, scan_type), use_container_width=True)
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
