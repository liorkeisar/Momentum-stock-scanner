import streamlit as st
import yfinance as yf
import pandas as pd
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time

st.set_page_config(layout="wide", page_title="TITAN: Professional Scanner")

@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT", "AMD", "TSLA"]

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean().iloc[-1]

def run_scanner(ticker, mode):
    try:
        time.sleep(0.05) # השהייה זעירה להגנה מפני חסימות
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        
        # סינון נזילות גמיש יותר
        if len(df) < 200 or df['Volume'].rolling(20).mean().iloc[-1] < 100000: return None
        
        curr_price = df['Close'].iloc[-1]
        atr = calculate_atr(df)
        stop_loss = round(curr_price - (2 * atr), 2)
        take_profit = round(curr_price + (6 * atr), 2)
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.20
        
        try: sector = stock.info.get('sector', 'Unknown')
        except: sector = 'Unknown'
        
        # סינונים גמישים יותר (BB_Width מ-10/15 ל-25)
        if mode == "מציאה" and df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 25:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': 100, 'Sector': sector}
        elif mode == "פריצה" and df['BB_Width'].iloc[-1] < 25 and df['RVOL'].iloc[-1] > 1.2:
            score = min(100, int((25 - df['BB_Width'].iloc[-1]) * 2 + (df['RVOL'].iloc[-1] * 10)))
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': score, 'Sector': sector}
    except: return None
    return None

st.title("🛡️ TITAN: ATR-Based Professional Scanner")
tab1, tab2 = st.tabs(["📉 מציאות", "🚀 פריצות"])

def render_tab(mode, filename):
    if st.button(f"סרוק {mode}"):
        with st.spinner("סורק מניות..."):
            results = []
            # הפחתה ל-10 עובדים כדי למנוע חסימה
            with ThreadPoolExecutor(max_workers=10) as ex:
                futures = [ex.submit(run_scanner, t, mode) for t in get_universe()[:300]]
                for f in futures:
                    res = f.result()
                    if res: results.append(res)
            
            if results:
                df = pd.DataFrame(results).sort_values(by='Score', ascending=False)
                df.to_csv(filename, index=False)
                st.session_state[mode] = df
            else: st.warning("לא נמצאו מניות. נסה שוב או בדוק חיבור.")

    if mode in st.session_state:
        st.dataframe(st.session_state[mode], use_container_width=True)
        st.download_button(f"📥 הורד אקסל {mode}", data=st.session_state[mode].to_csv(index=False), file_name=f"{mode}.csv")

with tab1: render_tab("מציאה", "res_val.csv")
with tab2: render_tab("פריצה", "res_brk.csv")
