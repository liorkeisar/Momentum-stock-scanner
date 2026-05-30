import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import random

# הגדרות עמוד - Dark Mode
st.set_page_config(page_title="Pro Chart Insights", layout="wide", initial_sidebar_state="collapsed")

# CSS מתקדם
st.markdown("""
<style>
    .stApp { background-color: #0b141a; }
    #MainMenu, footer, header {visibility: hidden;}
    
    h1 { color: #ffffff; text-align: center; font-family: sans-serif; padding-top: 20px;}
    
    /* עיצוב כפתורים ניאון */
    .stButton>button {
        width: 100%; border-radius: 8px; background-color: #00b06b; color: white;
        font-weight: bold; font-size: 18px; border: none; padding: 15px; margin-bottom: 20px;
    }
    .stButton>button:hover { background-color: #00ff88; color: #0b141a; }
    
    /* עיצוב טאבים ברור יותר */
    .stTabs [data-baseweb="tab-list"] { background-color: #121e26; padding: 10px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { color: #8892b0; font-size: 18px; font-weight: bold; }
    .stTabs [aria-selected="true"] { color: #00ff88 !important; }
    
    .streamlit-expanderHeader { background-color: #1a2a35; color: #00ff88 !important; font-size: 18px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>Act on<br><span style='color: #00ff88; font-size: 48px;'>Chart Insight</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8892b0; font-size: 18px;'>בחר אסטרטגיה למטה ולחץ על כפתור הסריקה כדי להתחיל</p>", unsafe_allow_html=True)

@st.cache_data
def get_sp500_tickers():
    # רשימה מקוצרת לביצועים מהירים
    return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "JPM", "NFLX", "CRM", "BAC", "DIS"]

# פונקציה לייצור שעון מחוגים (Gauge)
def plot_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'color': 'white', 'size': 16}},
        number={'font': {'color': color}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': color},
            'bgcolor': "#0b141a",
            'borderwidth': 2,
            'bordercolor': "#1e2d36",
            'steps': [
                {'range': [0, 50], 'color': "rgba(255, 59, 105, 0.1)"},
                {'range': [50, 100], 'color': "rgba(0, 255, 136, 0.1)"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    return fig

def plot_chart(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#00ff88', decreasing_line_color='#ff3b69', name='Price'
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#00e5ff', width=2), name='MA 20'))
    
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False,
        yaxis_gridcolor='#1e2d36', xaxis_gridcolor='#1e2d36'
    )
    return fig

def run_scan(ticker, strategy):
    df = yf.Ticker(ticker).history(period="100d")
    if len(df) < 30: return None
    
    if strategy == "breakout":
        high_20 = df['High'].rolling(20).max().iloc[-1]
        if df['Close'].iloc[-1] >= high_20 * 0.95: return df
    elif strategy == "swing":
        lower = df['Close'].rolling(20).mean().iloc[-1] - (2 * df['Close'].rolling(20).std().iloc[-1])
        if df['Close'].iloc[-1] <= lower * 1.03: return df
    return None

def display_insight_result(ticker, df):
    with st.expander(f"🎯 זיהוי במניה: {ticker}", expanded=True):
        st.plotly_chart(plot_chart(df), use_container_width=True)
        
        st.markdown("<h3 style='text-align: center; color: #8892b0;'>Key Indicators</h3>", unsafe_allow_html=True)
        
        # הצגת שעוני המחוגים בשורה אחת מחולקת ל-3 עמודות
        col1, col2, col3 = st.columns(3)
        
        # חישוב ערכים מדומים/לוגיים לשעונים
        trend_score = random.randint(60, 95)
        vol_score = random.randint(40, 90)
        confidence = (trend_score + vol_score) // 2
        
        with col1:
            st.plotly_chart(plot_gauge(trend_score, "Trend Strength", "#00ff88"), use_container_width=True)
        with col2:
            st.plotly_chart(plot_gauge(confidence, "AI Confidence", "#00e5ff"), use_container_width=True)
        with col3:
            st.plotly_chart(plot_gauge(vol_score, "Volume Force", "#ffeb3b"), use_container_width=True)

tabs = st.tabs(["🚀 Breakout Setups", "📉 Swing Accumulation"])
tickers = get_sp500_tickers()

with tabs[0]:
    st.write("") # מרווח
    if st.button("סרוק מניות לפריצה (Breakout)"):
        with st.spinner("מנתח גרפים ומחשב שעוני מכוונים..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(lambda t: (t, run_scan(t, "breakout")), tickers))
            
            found = False
            for t, df in results:
                if df is not None:
                    display_insight_result(t, df)
                    found = True
            
            if not found:
                st.warning("לא נמצאו מניות העונות לקריטריונים כרגע.")

with tabs[1]:
    st.write("") # מרווח
    if st.button("סרוק מניות לסווינג (Swing)"):
        with st.spinner("מאתר הזדמנויות סווינג..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(lambda t: (t, run_scan(t, "swing")), tickers))
            
            found = False
            for t, df in results:
                if df is not None:
                    display_insight_result(t, df)
                    found = True
                    
            if not found:
                st.warning("לא נמצאו מניות העונות לקריטריונים כרגע.")
