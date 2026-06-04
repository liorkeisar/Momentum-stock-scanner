import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Terminal v2", initial_sidebar_state="collapsed")

# --- CSS עיצוב פינטק פרימיום מודרני ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: -apple-system, sans-serif; }
    .main-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(90deg, #F1EFF7, #E2B4BD); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { color: #7E7497; font-size: 0.95rem; margin-bottom: 35px; }
    
    /* טאבים כפתורי קפסולה */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; border-bottom: 1px solid #1E1833; }
    .stTabs [data-baseweb="tab"] { background-color: #151026; border-radius: 20px; color: #938AA9; padding: 8px 20px; border: 1px solid #231B3D; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { background-color: #E2B4BD !important; color: #0A0712 !important; border-color: #E2B4BD !important; font-weight: 600; }
    
    /* כרטיסיות מניות */
    .premium-card { background: #120D24; border: 1px solid #1F173A; border-radius: 20px; padding: 24px; margin-bottom: 15px; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    .badge { padding: 6px 14px; border-radius: 30px; font-size: 0.8rem; font-weight: 600; }
    .badge-reversal { background-color: rgba(74, 212, 134, 0.12); color: #4AD486; }
    .badge-breakout { background-color: rgba(244, 162, 97, 0.12); color: #F4A261; }
    
    /* כפתור הפעלה */
    .stButton>button { background: linear-gradient(180deg, #241A42, #191230); color: #E6E1F3; border: 1px solid #33265C; border-radius: 14px; padding: 12px 28px; font-weight: 600; width: 100%; }
    .stButton>button:hover { border-color: #E2B4BD; color: #E2B4BD; }
    
    /* עיצוב רובריקות הבחירה למתנדים */
    div[data-testid="stCheckbox"] {
        background-color: #151026;
        border: 1px solid #231B3D;
        padding: 8px 16px;
        border-radius: 12px;
        transition: all 0.2s ease;
    }
    div[data-testid="stCheckbox"]:hover {
        border-color: #E2B4BD;
    }
    </style>
""", unsafe_allow_html=True)

# --- מאגר המניות המלא מחולק לקבוצות ---
MARKET_DATA = {
    "NASDAQ_A": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON", "AMAT", "QCOM", "BKNG", "ISRG", "VRTX"],
    "NASDAQ_B": ["MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT", "PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP"],
    "NASDAQ_C":
