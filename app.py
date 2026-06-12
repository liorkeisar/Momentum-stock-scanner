import streamlit as st
import yfinance as yf
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Persistant Scanner")

# --- ניהול קבצים ---
def save_results(results, mode):
    df_res = pd.DataFrame.from_dict(results, orient='index', columns=['Data', 'Score', 'Sector'])
    df_res[['Score', 'Sector']].to_csv(f"last_scan_{mode}.csv")

def load_results(mode):
    if os.path.exists(f"last_scan_{mode}.csv"):
        return pd.read_csv(f"last_scan_{mode}.csv", index_col=0)
    return None

# --- לוגיקה ---
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return df['Symbol'].dropna().unique().tolist()[:100] # קיצרתי ל-100 לבדיקה מהירה, תסיר את ה-[:100] כדי לסרוק הכל
    except: return ["AAPL", "NVDA", "MSFT"]

def run_scanner_ticker(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="100d")
        if len(hist) < 50: return None
        
        # חישובים בסיסיים
        ma20 = hist['Close'].rolling(20).mean().iloc[-1]
        bb_width = (hist['Close'].rolling(20).std() * 4 / ma20) * 100
        rvol = hist['Volume'].iloc[-1] / hist['Volume'].rolling(20).mean().iloc[-1]
        
        sector = stock.info.get('sector', 'Unknown')
        
        if mode == "מציאה" and bb_width < 10:
            return ticker, 100, sector
        elif mode == "פריצה" and bb_width < 15 and rvol > 1.2:
            score = min(100, int((15 - bb_width) * 3 + (rvol * 20)))
            return ticker, score, sector
    except: return None
    return None

# --- ממשק ---
st.title("🛡️ TITAN: Persistent Scanner")
tab1, tab2 = st.tabs(["📉 מציאות", "🚀 פריצות"])

def process_and_save(mode):
    results = {}
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(run_scanner_ticker, t, mode): t for t in get_universe()}
        for f in futures:
            res = f.result()
            if res: results[res[0]] = {'Score': res[1], 'Sector': res[2]}
    save_results(results, mode)
    return results

with tab1:
    if st.button("סרוק מציאות"): st.session_state['res_val'] = process_and_save("מציאה")
    res = st.session_state.get('res_val', load_results("מציאה"))
    if res is not None:
        st.dataframe(res)

with tab2:
    if st.button("סרוק פריצות"): st.session_state['res_brk'] = process_and_save("פריצה")
    res = st.session_state.get('res_brk', load_results("פריצה"))
    if res is not None:
        st.dataframe(res)
