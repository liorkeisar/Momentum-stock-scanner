import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Quantum Terminal")

# הזרקת CSS מרוכזת - זה מה שנותן את המראה המודרני
st.markdown("""
    <style>
    /* הגדרות כלליות לרקע כהה */
    .stApp { background-color: #0A0712 !important; color: #E6E1F3 !important; }
    
    /* כרטיסייה מעוצבת */
    .custom-card { 
        background-color: #111522; 
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #1F2538;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* כותרת */
    .ticker-header { font-size: 2rem; font-weight: 800; color: #FFFFFF; margin-bottom: 5px; }
    
    /* אינדיקטורים */
    .indicator-row { display: flex; justify-content: space-between; margin-top: 10px; border-bottom: 1px solid #1F2538; padding-bottom: 5px; }
    .indicator-val { color: #00B887; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

ticker = st.text_input("הזן סימול", value="NVDA")
if ticker:
    df = yf.Ticker(ticker).history(period="10d")
    
    # הצגה בתוך Div מעוצב
    st.markdown(f"""
    <div class="custom-card">
        <div class="ticker-header">{ticker}</div>
        <div style="font-size: 1.5rem; color: #00B887;">${df['Close'].iloc[-1]:.2f}</div>
        <div class="indicator-row">
            <span>RSI</span>
            <span class="indicator-val">54.7</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
