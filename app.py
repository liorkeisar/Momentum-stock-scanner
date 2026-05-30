import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🏹 Ultimate S&P 500 Trading Dashboard")

@st.cache_data
def get_sp500_tickers():
    return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", 
            "GS", "AVGO", "INTC", "NFLX", "CRM", "ADBE", "MS", "BAC", "WMT", "COST", "DIS", 
            "HD", "V", "MA", "PFE", "JNJ", "UNH", "XOM", "CVX", "MCD", "CAT", "DE", "IBM",
            "BA", "NKE", "SBUX", "MMM"] # הוספתי כמה חברות שנוטות לעשות תנועות תחתית חדות

# פונקציית גרף משודרגת עם תמיכה בצבעים וסמלים שונים
def plot_chart(df, ticker, signal_type, signal_color='green', symbol='triangle-up'):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers',
                             marker=dict(symbol=symbol, size=15, color=signal_color), name=signal_type))
    st.plotly_chart(fig, use_container_width=True)

def run_scan(ticker, strategy):
    # משיכת נתונים של שנה שלמה כדי שנוכל למצוא תחתית שנתית אמיתית
    df = yf.Ticker(ticker).history(period="1y")
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
        if len(df) >= 200 and df['Close'].iloc[-1] > df['Close'].rolling(200).mean().iloc[-1]:
            return df
            
    elif strategy == "yearly_bottom":
        # לוגיקה לתחתית שנתית: סריקת 252 ימי מסחר (שנה)
        if len(df) >= 250:
            yearly_low = df['Low'].min()
            # התנאי: מחיר הסגירה נמצא במרחק של עד 5% מהתחתית המוחלטת של השנה
            if df['Close'].iloc[-1] <= yearly_low * 1.05:
                return df
                
    return None

tabs = st.tabs(["🚀 פריצות (Breakout)", "📈 סווינג", "💎 טווח ארוך", "⚓ תחתית שנתית"])
tickers = get_sp500_tickers()

with tabs[0]:
    st.header("סורק פריצות (לחץ לפני מהלך)")
    if st.button("סרוק פריצות"):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda t: (t, run_scan(t, "breakout")), tickers))
        for t, df in results:
            if df is not None:
                with st.expander(f"מניה בלחץ לקראת פריצה: {t}"):
                    plot_chart(df, t, "Pre-Breakout")

with tabs[1]:
    st.header("סורק סווינג")
    if st.button("סרוק סווינג"):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda t: (t, run_scan(t, "swing")), tickers))
        for t, df in results:
            if df is not None:
                with st.expander(f"מניית סווינג (איסוף): {t}"):
                    plot_chart(df, t, "Bollinger Buy")

with tabs[2]:
    st.header("סורק טווח ארוך")
    if st.button("סרוק מגמה ארוכה"):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda t: (t, run_scan(t, "long")), tickers))
        for t, df in results:
            if df is not None:
                with st.expander(f"מניית מגמה חיובית: {t}"):
                    plot_chart(df, t, "Trend Follow")

with tabs[3]:
    st.header("סורק תחתית של 52 שבועות")
    if st.button("סרוק תחתית שנתית"):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda t: (t, run_scan(t, "yearly_bottom")), tickers))
        for t, df in results:
            if df is not None:
                with st.expander(f"מניה בתחתית שנתית: {t}"):
                    # שינוי צבע וסמל עבור זיהוי תחתית כדי להבדיל משאר האסטרטגיות
                    plot_chart(df, t, "Yearly Bottom", signal_color='blue', symbol='star')
