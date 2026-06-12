import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Multi-Strategy Scanner")

# --- ניהול שמירה ---
def save_to_disk(results, mode):
    # נמיר את ה-DataFrame לפורמט בסיסי לשמירה
    serializable_res = {t: {'score': s, 'sector': sec} for t, (df, s, sec) in results.items()}
    with open(f"scan_{mode}.json", "w") as f:
        json.dump(serializable_res, f)
    st.success(f"הסריקה נשמרה בהצלחה!")

def load_from_disk(mode):
    if os.path.exists(f"scan_{mode}.json"):
        with open(f"scan_{mode}.json", "r") as f:
            return json.load(f)
    return None

def clear_disk(mode):
    if os.path.exists(f"scan_{mode}.json"):
        os.remove(f"scan_{mode}.json")
        st.warning(f"השמירה נמחקה.")

# --- טעינה ולוגיקה (נשאר זהה) ---
@st.cache_data(ttl=86400)
def get_universe():
    try:
        url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT"]

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        info = stock.info
        sector = info.get('sector', 'Unknown')
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        if mode == "מציאה" and df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
            return ticker, df, 100, sector
        elif mode == "פריצה" and df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
            score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
            return ticker, df, score, sector
    except: return None
    return None

def process_scan(mode):
    tickers = get_universe()
    progress_bar = st.progress(0)
    results = {}
    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(run_scanner, t, mode): t for t in tickers}
        for i, future in enumerate(futures):
            res = future.result()
            if res: results[res[0]] = (res[1], res[2], res[3])
            progress_bar.progress((i + 1) / len(tickers))
    return dict(sorted(results.items(), key=lambda item: item[1][1], reverse=True))

# --- ממשק ---
st.title("🛡️ TITAN: Multi-Strategy Scanner")
tab1, tab2 = st.tabs(["📉 מניות במחיר מציאה", "🚀 מניות לפני פריצה"])

def render_tab(mode, session_key, label):
    if st.button(f"🚀 סרוק {label}"):
        st.session_state[session_key] = process_scan(mode)
    
    # טעינה אוטומטית אם יש שמירה
    saved_res = load_from_disk(mode)
    if saved_res and session_key not in st.session_state:
        st.session_state[session_key] = saved_res
        
    if session_key in st.session_state:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"💾 שמור תוצאות {label}", key=f"save_{mode}"):
                save_to_disk(st.session_state[session_key], mode)
        with col2:
            if st.button(f"🗑️ מחק שמירה {label}", key=f"del_{mode}"):
                clear_disk(mode)
                del st.session_state[session_key]
                st.rerun()
        
        for t, data in st.session_state[session_key].items():
            st.write(f"---")
            # טיפול בנתונים משמירה (JSON) לעומת תוצאת סורק
            sec = data['sector'] if isinstance(data, dict) else data[2]
            score = data['score'] if isinstance(data, dict) else data[1]
            st.write(f"**מניה:** {t} | **סקטור:** {sec} | **ציון:** {score}")

with tab1: render_tab("מציאה", "res_val", "מציאות")
with tab2: render_tab("פריצה", "res_brk", "פריצות")
