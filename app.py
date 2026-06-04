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
    "NASDAQ_C": ["AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR", "ON", "EXC", "MRVL", "CTSH", "EA", "CDNS", "ABNB", "CEG", "MDB", "VRSK", "FAST", "CSX", "DXCM", "ANSS", "FFIV"],
    "NASDAQ_D": ["SBAC", "ALGN", "EBAY", "SIRI", "ZBRA", "ILMN", "WBA", "JD", "BIDU", "LCID", "ZM", "MRNA", "PYPL", "INTC", "MU", "DLTR", "EXPE", "LULU"],
    "SP500_A": ["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "BRK.B", "TSLA", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "LLY", "COST", "PEP", "ADBE", "WMT", "MCD", "CSCO", "CRM", "BAC"],
    "SP500_B": ["ACN", "TMO", "LIN", "ORCL", "AMD", "CMCSA", "ABT", "TXN", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "GE", "AXP", "T", "DHR", "PLD", "SBUX", "CAT", "BA", "DE", "ISRG", "HON", "LOW", "SPGI", "BLK", "NOW"],
    "DOW_FULL": ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"],
    "MIDCAP": ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE"]
}

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        
        # חישוב מתנדים בסיסיים לסריקה וגרפים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        df['Vol20'] = df['Volume'].rolling(20).mean()
        
        # חישוב אינדיקטורים מורחבים
        std20 = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['MA20'] + (std20 * 2)
        df['BB_Lower'] = df['MA20'] - (std20 * 2)
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # MFI (Money Flow Index)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        rmf = tp * df['Volume']
        pos_flow = rmf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg_flow = rmf.where(tp < tp.shift(1), 0).rolling(14).sum()
        df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow)))
        
        if scan_type == "REVERSAL":
            if df['Close'].iloc[-1] > df['MA20'].iloc[-1] and df['Close'].iloc[-2] < df['MA20'].iloc[-2]:
                return ticker, df
        elif scan_type == "BREAKOUT":
            if df['Close'].iloc[-1] > df['High20'].iloc[-1] and df['Volume'].iloc[-1] > df['Vol20'].iloc[-1]:
                return ticker, df
    except: return None
    return None

def draw_premium_chart(df, ticker, mode, show_bb, show_rsi, show_macd, show_mfi):
    df_clean = df.copy()
    if df_clean.index.tz is not None:
        df_clean.index = df_clean.index.tz_localize(None)
        
    df_slice = df_clean.tail(30)
    
    # קביעת כמות פאנלים (Subplots) לפי המתנדים שנבחרו
    rows = 1
    row_heights = [1.0]
    
    if show_rsi: rows += 1; row_heights.append(0.3)
    if show_macd: rows += 1; row_heights.append(0.3)
    if show_mfi: rows += 1; row_heights.append(0.3)
    
    # נרמול גבהים מחדש של הפאנלים
    total_weight = sum(row_heights)
    row_heights = [h/total_weight for h in row_heights]
    
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=row_heights, vertical_spacing=0.05)
    
    # 1. גרף מחיר ראשי - שטח מוצלל (Gradient Area Style)
    fig.add_trace(go.Scatter(
        x=df_slice.index, y=df_slice['Close'], 
        line=dict(color='#E2B4BD', width=2.5), 
        fill='tozeroy', fillcolor='rgba(226, 180, 189, 0.04)',
        name='Price'
    ), row=1,
