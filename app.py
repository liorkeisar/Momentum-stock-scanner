import streamlit as st
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Reversal Divergence Scanner", layout="wide")

@st.cache_data
def get_sp500_tickers():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        df = pd.read_html(url)[0]
        return df['Symbol'].tolist()
    except:
        return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA"]

def calculate_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MFI
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    mf = typical_price * df['Volume']
    pos_mf = mf.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
    neg_mf = mf.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos_mf / neg_mf)))
    
    return df

def run_scanner(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if len(df) < 50: return None
        df = calculate_indicators(df)
        
        # תנאים:
        # 1. RSI ב-Oversold ועולה (היום גבוה מאתמול)
        rsi_condition = (df['RSI'].iloc[-1] < 40) and (df['RSI'].iloc[-1] > df['RSI'].iloc[-2])
        # 2. MFI עולה
        mfi_condition = (df['MFI'].iloc[-1] > df['MFI'].iloc[-2])
        # 3. מחיר קרוב לשפל שנתי
        price_condition = (df['Close'].iloc[-1] <= df['Low'].min() * 1.08)
        
        if rsi_condition and mfi_condition and price_condition:
            return df
    except:
        return None
    return None

st.title("🛡️ Divergence Reversal Scanner")
tickers = get_sp500_tickers()

if st.button("🔍 סרוק S&P 500 לסיגנל היפוך"):
    with st.spinner("סורק מניות..."):
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(run_scanner, tickers))
            
        found_any = False
        for i, df in enumerate(results):
            if df is not None:
                st.write(f"---")
                st.subheader(f"סיגנל ב-{tickers[i]}")
                st.write(f"RSI: {df['RSI'].iloc[-1]:.1f} (עולה) | MFI: {df['MFI'].iloc[-1]:.1f} (עולה)")
                st.line_chart(df['Close'].tail(50))
                found_any = True
        
        if not found_any:
            st.warning("לא נמצאו מניות העונות על הקריטריונים כרגע.")
def run_breakout_scan(ticker):
    try:
        df = yf.Ticker(ticker).history(period="60d")
        if len(df) < 40: return None
        
        # חישוב אינדיקטורים
        df['MA_Vol'] = df['Volume'].rolling(20).mean()
        df['High_20'] = df['High'].rolling(20).max().shift(1) # שיא של 20 יום לא כולל היום
        
        # תנאי פריצה
        is_breaking_out = df['Close'].iloc[-1] > df['High_20'].iloc[-1]
        is_volume_high = df['Volume'].iloc[-1] > df['MA_Vol'].iloc[-1] * 1.5 # נפח גבוה ב-50% מהממוצע
        
        if is_breaking_out and is_volume_high:
            return ticker, df
    except:
        return None
    return None
