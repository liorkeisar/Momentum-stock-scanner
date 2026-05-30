import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import random

st.set_page_config(page_title="S&P 500 Scanner", layout="wide")

# פונקציה למשיכת כל ה-S&P 500 אוטומטית
@st.cache_data(ttl=86400) # שמירה בזיכרון ליום שלם
def get_sp500_tickers():
    try:
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = table[0]
        return df['Symbol'].tolist()
    except:
        return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA"] # גיבוי למקרה של תקלה

def plot_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={'text': title, 'font': {'color': 'white'}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': color}}
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    return fig

# ... (שאר פונקציות ה-plot_chart, run_scan ו-render_key_insights נשארות זהות) ...

st.title("⚡ S&P 500 Momentum Scanner")

tickers = get_sp500_tickers()
st.info(f"מחובר ל-Yahoo Finance: סורק כעת {len(tickers)} מניות מתוך ה-S&P 500")

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 סרוק את כל ה-S&P 500 (Breakout)"):
        with st.spinner("סורק את השוק..."):
            # כאן אנחנו סורקים את כל הרשימה
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(lambda t: (t, run_scan(t, "breakout")), tickers))
            
            count = 0
            for t, df in results:
                if df is not None:
                    display_insight_result(t, df)
                    count += 1
            st.success(f"סיום! נמצאו {count} הזדמנויות.")

with col2:
    if st.button("📉 סרוק את כל ה-S&P 500 (Swing)"):
        with st.spinner("סורק את השוק..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(lambda t: (t, run_scan(t, "swing")), tickers))
            
            count = 0
            for t, df in results:
                if df is not None:
                    display_insight_result(t, df)
                    count += 1
            st.success(f"סיום! נמצאו {count} הזדמנויות.")
