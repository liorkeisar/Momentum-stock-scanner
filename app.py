import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Reversal Scanner", layout="wide")

@st.cache_data
def get_sp500_tickers():
    # רשימה מקוצרת לטובת יציבות הסריקה
    return ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "JPM", "NFLX", "CRM", "BAC", "DIS", "INTC", "PEP", "KO", "GS", "AVGO", "WMT", "COST"]

def calculate_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # MFI (Money Flow Index)
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
    mfi = 100 - (100 / (1 + (positive_flow / negative_flow)))
    df['MFI'] = mfi
    
    return df

def run_reversal_scan(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if len(df) < 100: return None
        df = calculate_indicators(df)
        
        # התנאים שלך:
        # 1. שפל שנתי (המחיר הנוכחי קרוב למינימום של השנה)
        is_yearly_low = df['Close'].iloc[-1] <= df['Low'].min() * 1.05
        # 2. MACD עולה (והיה מתחת ל-0)
        is_macd_rising = df['MACD'].iloc[-1] > df['MACD'].iloc[-2] and df['MACD'].iloc[-1] < 0
        # 3. RSI באובר-סולד (מתחת ל-30)
        is_rsi_oversold = df['RSI'].iloc[-1] < 30
        # 4. MFI במגמת עלייה
        is_mfi_rising = df['MFI'].iloc[-1] > df['MFI'].iloc[-2]
        
        if is_yearly_low and is_macd_rising and is_rsi_oversold and is_mfi_rising:
            return df
    except:
        return None
    return None

st.title("🛡️ Reversal Signal Scanner")
tickers = get_sp500_tickers()

if st.button("🔍 סרוק מניות במצב Reversal (S&P 500)"):
    with st.spinner("מנתח אינדיקטורים טכניים..."):
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(run_reversal_scan, tickers))
            
        found = False
        for i, df in enumerate(results):
            if df is not None:
                st.success(f"נמצא סיגנל ב-{tickers[i]}")
                st.write(f"RSI: {df['RSI'].iloc[-1]:.2f} | MFI: {df['MFI'].iloc[-1]:.2f}")
                st.line_chart(df[['Close']])
                found = True
        
        if not found:
            st.warning("לא נמצאו מניות העונות על כל התנאים כרגע.")
