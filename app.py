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
    # חישוב ממוצעים נעים עבור הגרף (כמו בתמונה)
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

    # ווליום בתחתית הגרף
    colors = ['#00ff88' if row.Close >= row.Open else '#ff3b69' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, yaxis='y2', opacity=0.3, name='Volume'))

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_rangeslider_visible=False,
        showlegend=False,
        yaxis=dict(domain=[0.3, 1]),
        yaxis2=dict(domain=[0, 0.2], showticklabels=False),
        xaxis=dict(showgrid=False),
        yaxis_showgrid=True,
        yaxis_gridcolor='#1e2d36'
    )
    return fig

# פונקציה לבניית המדדים המעגליים (Key Insights) בעזרת HTML
def render_key_insights(df):
    # לוגיקה ליצירת התובנות
    current_close = df['Close'].iloc[-1]
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    vol = df['Volume'].iloc[-1]
    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
    
    trend = "Bullish" if current_close > ma20 else "Bearish"
    trend_color = "#00ff88" if trend == "Bullish" else "#ff3b69"
    trend_icon = "↗️" if trend == "Bullish" else "↘️"
    
    volume_status = "High" if vol > avg_vol else "Low"
    vol_color = "#00e5ff" if volume_status == "High" else "#8892b0"
    
    confidence_score = random.randint(75, 95) # ציון סמך המדמה אלגוריתם שקלול
    
    html = f"""
    <div style="background-color: #121e26; border-radius: 20px; padding: 20px; margin-top: 10px;">
        <h4 style="text-align: center; color: #8892b0; margin-bottom: 25px; font-weight: normal;">Key Insights</h4>
        <div style="display: flex; justify-content: space-between; align-items: center; max-width: 400px; margin: 0 auto;">
            
            <div style="display: flex; flex-direction: column; gap: 20px;">
                <div style="text-align: center;">
                    <div style="width: 55px; height: 55px; border-radius: 50%; border: 2px solid #005f73; background: linear-gradient(145deg, #0a1117, #15222b); display: flex; align-items: center; justify-content: center; margin: 0 auto; font-size: 20px; box-shadow: inset 0 0 10px rgba(0,229,255,0.1);">
                        {trend_icon}
                    </div>
                    <div style="font-size: 12px; color: #8892b0; margin-top: 5px;">Trend<br><span style="color: {trend_color}; font-weight: bold;">{trend}</span></div>
                </div>
                <div style="text-align: center;">
                    <div style="width: 55px; height: 55px; border-radius: 50%; border: 2px solid #005f73; background: linear-gradient(145deg, #0a1117, #15222b); display: flex; align-items: center; justify-content: center; margin: 0 auto; font-size: 20px;">
                        📊
                    </div>
                    <div style="font-size: 12px; color: #8892b0; margin-top: 5px;">Volume<br><span style="color: {vol_color}; font-weight: bold;">{volume_status}</span></div>
                </div>
            </div>
            
            <div style="text-align: center;">
                <div style="width: 110px; height: 110px; border-radius: 50%; border: 6px solid #00ff88; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(0, 255, 136, 0.3), inset 0 0 15px rgba(0, 255, 136, 0.2);">
                    <div>
                        <span style="font-size: 32px; font-weight: bold; color: #00ff88;">{confidence_score}%</span>
                    </div>
                </div>
                <div style="font-size: 12px; color: #8892b0; margin-top: 10px;">Confidence<br>Score</div>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 20px;">
                <div style="text-align: center;">
                    <div style="width: 55px; height: 55px; border-radius: 50%; border: 2px solid #005f73; background: linear-gradient(145deg, #0a1117, #15222b); display: flex; align-items: center; justify-content: center; margin
