import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="Quantum Terminal TITAN Pro")

# --- רשימות שוק ---
MARKET_DATA = {
    "AI_TECH": ["NVDA", "AMD", "MSFT", "GOOGL", "AVGO", "PLTR", "SNPS", "CDNS", "ARM", "TSM", "AAPL", "META", "AMZN", "INTC", "ADBE"],
    "ENERGY": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL", "DUK", "AEP", "EXC", "XEL", "PEG"],
    "NASDAQ": ["PAYX", "CPRT", "ROST", "KDP", "CHTR", "ANSS", "TEAM", "DDOG", "FAST", "MCHP", "GILD", "EA", "CTSH", "IDXX", "ADI", "BKR", "ON", "MRVL", "ABNB", "CEG", "MDB", "VRSK", "CSX", "DXCM", "FFIV", "ILMN", "WBA", "ZBRA", "ALGN", "VRSN", "EBAY", "SIRI", "NTES", "JD", "BIDU", "LCID", "BILI", "OKTA", "SPLK", "FITB", "FANG", "MGM", "SBUX", "WBD", "MKTX", "DLTR", "URI", "EXPE", "KVUE"],
    "SP500": ["BRK.B", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY", "WMT", "MCD", "CRM", "BAC", "ACN", "TMO", "LIN", "ORCL", "CMCSA", "ABT", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "LOW", "SCHW", "SPGI", "UNP", "T", "DIS", "INTC", "BMY", "TXN", "RTX", "GE", "AXP", "CAT", "PGR", "C", "GS", "WFC", "BLK", "NOW", "PLTR", "UBER", "IBM", "DE", "MMM", "LMT", "SYK", "MDT", "CI", "TJX", "MO", "NOC", "COF", "LRCX", "KLAC", "MU", "EQIX", "PSA", "PLD", "AMT", "CCI", "WY", "SPG", "DLR", "O", "WELL", "AVB", "EQR", "VTR", "BXP", "REG", "MAA", "UDR", "ESS", "PEAK", "DOC", "ARE", "FRT", "ETR", "FE", "AEE", "CMS", "ED", "D", "SO"],
    "MIDCAP_RUSSELL": ["POOL", "FDS", "PNR", "RS", "TKO", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE", "XPO", "AFRM", "HOOD", "SOFI", "DKNG", "RBLX", "TOST", "UPST", "AI", "PATH", "IOT", "U", "SNOW", "NET", "FSLR", "ENPH", "SEDG", "RUN", "PLUG", "CHPT", "BLINK", "RIVN", "LCID", "QS", "RKLB", "SPCE", "BABA", "LI", "NIO", "XPEV", "FUTU", "SE", "SHOP", "SQ", "PYPL", "COIN", "MARA", "RIOT", "CLSK", "WULF", "IREN", "HUT", "CORZ", "MSTR", "GME", "AMC", "DJT", "RDDT", "CELH", "WING", "FRSH", "APP", "PSTG", "NTNX", "NVAX", "MRNA", "BNTX", "CRSP", "EDIT", "BEAM", "NTLA", "PACB", "ILMN", "EXAS", "GH", "GUARD", "FGEN", "BYND", "OTLY", "HIMS", "SOUN", "BBAI", "CXAI", "PLTR", "VNDA", "PETQ", "GPRO", "WKHS", "NKLA", "ASTR", "MNMD", "CYBN", "CMPS", "ATAI", "BMEA", "KPTI", "GERN", "BCAB", "XFOR", "CLSD", "EYEN", "OCUP", "OBLG", "SENS", "AMAM", "VERV", "BEAM", "CRBU", "CLLS", "DTIL", "EDIT", "FDMT", "NTLA", "SANA", "SGMO", "VIGL", "ZENTAL", "DRRX", "SCYX", "VYGR", "LRE", "AOUT", "SWBI", "RGR", "POWW", "VSTO", "DKS", "BGFV", "HIBB", "BOOT", "CAL", "DECK", "SKX", "WOLV", "IEP", "AMR", "ARCH", "HCC", "CEIX", "BTU", "YAVY", "AAL", "ALGT", "HA", "SAVE", "BLNK", "EVGO", "CHPT", "BE", "FCEL", "PLUG", "AMRC", "CWEN", "AY", "NOVA", "RUN", "SUNW", "MAXN", "SHLS", "ARRY", "FTCI", "NXT", "ENPH", "SEDG", "DDD", "SSYS", "DM", "MKFG", "VLD", "XONE", "PRLB", "NNDM", "SGLY", "MIND", "KTOS", "AVAV", "RADA", "ASTR", "BKSY", "PL", "SATL", "LLAP", "SIDU", "QUBT"]
}

# --- לוגיקה ---
@st.cache_data(ttl=3600)
def get_data(ticker): return yf.Ticker(ticker).history(period="300d")

def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
    df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
    df['MFI'] = 100 - (100 / (1 + (df['Volume'] * ((df['High']+df['Low']+df['Close'])/3)).rolling(14).mean()))
    df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
    
    # MACD Calculation
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def run_scanner(ticker):
    try:
        df = get_data(ticker)
        if len(df) < 252: return None
        df = calculate_indicators(df)
        last = df.iloc[-1]
        # תנאי מוסדי מעודכן: ירידה + כיווץ + MFI + RVOL + MACD חיובי
        if last['is_dropped'] and last['BB_Width'] < 10 and last['MFI'] > 45 and last['RVOL'] > 1.5 and last['MACD'] > last['Signal']:
            return ticker, df
    except: return None
    return None

# --- ממשק ---
st.title("🛡️ Quantum Terminal TITAN")
tab1, tab2 = st.tabs(["🚀 סריקה מוסדית מקיפה", "🔍 סריקה ידנית פרטנית"])

with tab1:
    selected_sector = st.selectbox("בחר סקטור:", list(MARKET_DATA.keys()) + ["ALL_MARKET"])
    if st.button("הפעל סורק סקטוריאלי"):
        tickers = []
        if selected_sector == "ALL_MARKET":
            for group in MARKET_DATA.values(): tickers.extend(group)
        else: tickers = MARKET_DATA[selected_sector]
        
        with ThreadPoolExecutor(max_workers=20) as ex:
            results = list(ex.map(run_scanner, tickers))
            st.session_state['results'] = {r[0]: r[1] for r in results if r is not None}

with tab2:
    manual_ticker = st.text_input("הזן סימול מניה לבדיקה ידנית:").upper()
    if st.button("סרוק מניה בודדת"):
        res = run_scanner(manual_ticker)
        if res: st.session_state['results'] = {res[0]: res[1]}
        else: st.warning("המניה לא עומדת בקריטריונים המוסדיים.")

if 'results' in st.session_state:
    for ticker, df in st.session_state['results'].items():
        st.subheader(f"תוצאה: {ticker}")
        fig = go.Figure(data=[go.Candlestick(x=df.index[-90:], open=df['Open'][-90:], high=df['High'][-90:], low=df['Low'][-90:], close=df['Close'][-90:])])
        st.plotly_chart(fig, use_container_width=True)
        st.write(f"אינדיקטורים: RVOL: {df['RVOL'].iloc[-1]:.1f}x | MACD: {'חיובי' if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else 'שלילי'}")
