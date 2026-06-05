import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Terminal v2", initial_sidebar_state="collapsed")

# --- CSS עיצוב פינטק פרימיום מודרני ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: -apple-system, sans-serif; }
    .main-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(90deg, #00B887, #E2B4BD); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { color: #7E7497; font-size: 0.95rem; margin-bottom: 35px; }
    
    /* טאבים */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; border-bottom: 1px solid #1E1833; }
    .stTabs [data-baseweb="tab"] { background-color: #151026; border-radius: 20px; color: #938AA9; padding: 8px 20px; border: 1px solid #231B3D; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { background-color: #2D2447 !important; color: #00B887 !important; border-color: #00B887 !important; font-weight: 600; }
    
    /* כרטיסיית מניה משולבת */
    .stock-container { background: #0B0E14; border: 1px solid #1F2433; border-radius: 16px; padding: 16px; margin-bottom: 20px; }
    .info-panel { background: #111522; border: 1px solid #1F2538; border-radius: 12px; padding: 14px; height: 100%; display: flex; flex-direction: column; justify-content: flex-start; }
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; display: block; }
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; margin-top: 6px; text-align: center; }
    .badge-reversal { background-color: rgba(0, 184, 135, 0.15); color: #00B887; }
    .badge-breakout { background-color: rgba(255, 159, 28, 0.15); color: #FF9F1C; }
    .badge-search { background-color: rgba(58, 134, 255, 0.15); color: #3A86FF; }
    
    /* פאנל סיבת איתות מקצועי */
    .trigger-reason-box { background: rgba(255, 255, 255, 0.03); border: 1px dashed #2D3748; border-radius: 8px; padding: 8px 10px; margin-top: 12px; font-size: 0.75rem; line-height: 1.3; }
    .trigger-title { color: #E2B4BD; font-weight: 600; display: block; margin-bottom: 3px; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* אלמנטים של אינדיקטורים במקרא */
    .indicator-box { margin-top: 12px; padding-top: 8px; border-top: 1px solid #1F2538; }
    .indicator-row { display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 4px; }
    .indicator-name { color: #938AA9; font-weight: 500; }
    .indicator-desc { color: #5C5374; font-size: 0.7rem; display: block; margin-bottom: 6px; line-height: 1.1; }
    
    /* כפתור הפעלה ותיבות קלט */
    .stButton>button { background: linear-gradient(180deg, #1A202C, #0B0E14); color: #E6E1F3; border: 1px solid #2D3748; border-radius: 12px; padding: 10px 24px; font-weight: 600; width: 100%; transition: all 0.3s; }
    .stButton>button:hover { border-color: #00B887; color: #00B887; }
    div[data-testid="stTextInput"] input { background-color: #111522 !important; color: #FFFFFF !important; border: 1px solid #1F2538 !important; border-radius: 10px !important; }
    div[data-testid="stTextInput"] input:focus { border-color: #00B887 !important; }
    </style>
""", unsafe_allow_html=True)

MARKET_DATA = {
    "NASDAQ_A": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON", "AMAT", "QCOM", "BKNG", "ISRG", "VRTX"],
    "NASDAQ_B": ["MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT", "PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP"],
    "NASDAQ_C": ["AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR", "ON", "EXC", "MRVL", "CTSH", "EA", "CDNS", "ABNB", "CEG", "MDB", "VRSK", "FAST", "CSX", "DXCM", "ANSS", "FFIV"],
    "NASDAQ_D": ["SBAC", "ALGN", "EBAY", "SIRI", "ZBRA", "ILMN", "WBA", "JD", "BIDU", "LCID", "ZM", "MRNA", "PYPL", "INTC", "MU", "DLTR", "EXPE", "LULU"],
    "SP500_A": ["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "BRK.B", "TSLA", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "LLY", "COST", "PEP", "ADBE", "WMT", "MCD", "CSCO", "CRM", "BAC"],
    "SP500_B": ["ACN", "TMO", "LIN", "ORCL", "AMD", "CMCSA", "ABT", "TXN", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "GE", "AXP", "T", "DHR", "PLD", "SBUX", "CAT", "BA", "DE", "ISRG", "HON", "LOW", "SPGI", "BLK", "NOW"],
    "DOW_FULL": ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"],
    "MIDCAP": ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE"]
}

def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['High20'] = df['High'].rolling(20).max().shift(1)
    df['Vol20'] = df['Volume'].rolling(20).mean()
    
    std20 = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (std20 * 2)
    df['BB_Lower'] = df['MA20'] - (std20 * 2)
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    rmf = tp * df['Volume']
    pos_flow = rmf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg_flow = rmf.where(tp < tp.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow)))
    
    df['Buy_Signal'] = ((df['Close'] > df['MA20']) & (df['Close'].shift(1) <= df['MA20'].shift(1))) | \
                       ((df['Close'] > df['High20']) & (df['Volume'] > df['Vol20']))
                       
    df['Sell_Signal'] = (df['Close'] < df['MA20']) & (df['Close'].shift(1) >= df['MA20'].shift(1))
    return df

def get_trigger_reason(df, active_mode):
    """מייצרת ניתוח טכני מקצועי ומתמטי של סיבת האיתות הנוכחית"""
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    if active_mode == "REVERSAL":
        return f"פירסינג שורי של ממוצע נע 20 יום. מחיר סגירה הנוכחי (${last_row['Close']:.2f}) חצה מלמטה למעלה את ה-MA20 שעמד על ${last_row['MA20']:.2f}, מה שמעיד על שינוי מומנטום קצר טווח ומעבר משליטה דובת לשליטה שורית."
    elif active_
