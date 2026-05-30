import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

# הגדרות תצורה מודרניות לעמוד
st.set_page_config(page_title="Pro Scanner", layout="wide", initial_sidebar_state="collapsed")

# הזרקת CSS לעיצוב מודרני
st.markdown("""
<style>
    /* הסתרת תפריטים עליונים וזכויות יוצרים של Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* עיצוב כפתורים מודרני (Gradient) */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 14px rgba(50, 50, 93, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
    }
    
    /* עיצוב טאבים מודרני */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Pro Trading Dashboard")
st.markdown("---")

@st.cache_data
def get_sp500_tickers():
    return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", 
            "GS", "AVGO", "INTC", "NFLX", "CRM", "ADBE", "MS", "BAC", "WMT", "COST", "DIS", 
            "HD", "V", "MA", "PFE", "JNJ", "UNH", "XOM", "CVX", "MCD", "CAT", "DE", "IBM",
            "BA", "NKE", "SBUX", "MMM"]

# פונקציית גרף מודרנית כהה
def plot_chart(df, ticker, signal_type, signal_color='#00ff00', symbol='triangle-up'):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    fig.add_trace(go.Scatter(
        x=[df.index[-1]], y=[df['Close'].iloc[-1]], mode='markers',
        marker=dict(symbol=symbol, size=16, color=signal_color, line=dict(color='white', width=1)), 
        name=signal_type
    ))
    # עיצוב מודרני של הגרף עצמו
    fig.update_layout(
        template='plotly_dark',
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_rangeslider_visible=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

def run_scan(ticker, strategy):
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
        if len(df) >= 250:
            yearly_low = df['Low'].min()
            if df['Close'].iloc[-1] <= yearly_low * 1.05:
                return df
                
    return None

# פונקציית תצוגה מודרנית בתוך חלונית נפתחת
def display_modern_result(t, df, title, color, symbol):
    with st.expander(f"📌 {title}: {t}"):
        col1, col2 = st.columns([1, 4]) # חלוקה לעמודת נתונים ועמודת גרף
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        with col1:
            st.markdown("<br>", unsafe_allow_html=True)
            st.
