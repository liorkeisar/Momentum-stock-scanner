import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import random

# הגדרות תצורה מודרניות - Dark Mode
st.set_page_config(page_title="Pro Chart Insights", layout="wide", initial_sidebar_state="collapsed")

# הזרקת CSS לעיצוב שמדמה את האפליקציה בתמונה
st.markdown("""
<style>
    /* צבע רקע כללי כהה מאוד */
    .stApp {
        background-color: #0b141a;
    }
    
    /* הסתרת אלמנטים מיותרים של סטרימליט */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* עיצוב כותרת ראשית */
    h1 {
        color: #ffffff;
        text-align: center;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* כפתורי סריקה בסגנון ניאון ירוק */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        background-color: #00b06b;
        color: white;
        font-weight: bold;
        font-size: 16px;
        border: none;
        padding: 12px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #00ff88;
        color: #0b141a;
        transform: scale(1.02);
    }
    
    /* עיצוב הטאבים */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #121e26;
        border-radius: 10px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8892b0;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #00ff88 !important;
    }
    
    /* עיצוב תיבות ההרחבה */
    .streamlit-expanderHeader {
        background-color: #121e26;
        color: white !important;
        border-radius: 8px;
    }
    div[data-testid="stExpander"] {
        background-color: #0b141a;
        border: 1px solid #1e2d36;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>Act on<br><span style='color: #00ff88; font-size: 42px;'>Chart Insight</span></h1>", unsafe_allow_html=True)

@st.cache_data
def get_sp500_tickers():
    return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "PEP", "KO", "JPM", 
            "GS", "AVGO", "INTC", "NFLX", "CRM", "ADBE", "MS", "BAC", "WMT", "COST", "DIS", "BA"]

def plot_chart(df):
    # חישוב ממוצעים נעים עבור הגרף
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()

    fig = go.Figure()
    
    # נרות יפניים בסגנון ניאון
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#00ff88', decreasing_line_color='#ff3b69', name='Price'
    ))
    
    # קווים חלקים
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#00e5ff', width=1.5), name='MA 20'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='#8892b0', width=1.5, dash='dot'), name='MA 50'))

    # וול
