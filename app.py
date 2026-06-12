import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

def get_market_data():
    try:
        return yf.Ticker("^GSPC").history(period="300d")
    except: return pd.DataFrame()

def calculate_rs(stock_df, market_df):
    try:
        if market_df.empty: return 0
        stock_pct = stock_df['Close'].pct_change(20).iloc[-1]
        market_pct = market_df['Close'].pct_change(20).iloc[-1]
        return round((stock_pct - market_pct) * 100, 2)
    except: return 0

def run_scanner(ticker, mode, market_data):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252: return None
        
        curr_price = df['Close'].iloc[-1]
        # חישוב ATR בטוח
        high_low = df['High'] - df['Low']
        atr = high_low.rolling(14).mean().iloc[-1]
        
        rs = calculate_rs(df, market_data)
        stop_loss = round(curr_price - (2 * atr), 2)
        take_profit = round(curr_price + (6 * atr), 2)
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        data = {'Ticker': ticker, 'Price': round(curr_price, 2), 'RS': rs, 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': 0, 'Sector': stock.info.get('sector', 'Unknown')}
        
        if mode == "מציאה" and df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
            data['Score'] = 100
            return data
        elif mode == "פריצה" and df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
            data['Score'] = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
            return data
    except: return None
    return None

st.title("🛡️ TITAN: Professional Scanner")
tab1, tab2 = st.tabs(["📉 מציאות", "🚀 פריצות"])

def render_tab(mode, filename):
    if st.button(f"סרוק {mode}"):
        with st.spinner("סורק מניות ומנתח עוצמה..."):
            market_data = get_market_data()
            results = []
            with ThreadPoolExecutor(max_workers=30) as ex:
                futures = [ex.submit(run_scanner, t, mode, market_data) for t in get_universe()]
                for f in futures:
                    res = f.result()
                    if res: results.append(res)
            
            if results:
                df = pd.DataFrame(results).sort_values(by='Score', ascending=False)
                df.to_csv(filename, index=False)
                st.session_state[mode] = df
            else: st.warning("לא נמצאו מניות.")

    if mode not in st.session_state and os.path.exists(filename):
        st.session_state[mode] = pd.read_csv(filename)
    
    if mode in st.session_state:
        df = st.session_state[mode]
        def highlight_rs(val): return f'color: {"green" if val > 0 else "red"}'
        # שימוש ב-map לתיקון שגיאות תצוגה
        st.dataframe(df.style.map(highlight_rs, subset=['RS']), use_container_width=True)
        st.download_button(f"📥 הורד אקסל {mode}", data=df.to_csv(index=False), file_name=f"{mode}.csv")

with tab1: render_tab("מציאה", "res_val.csv")
with tab2: render_tab("פריצה", "res_brk.csv")
