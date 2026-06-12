import streamlit as st
import yfinance as yf
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Trading System")

@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT"]

def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        curr_price = df['Close'].iloc[-1]
        # ניהול סיכונים: 3% הפסד, 9% יעד (יחס 1:3)
        stop_loss = round(curr_price * 0.97, 2)
        take_profit = round(curr_price * 1.09, 2)
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        try: sector = stock.info.get('sector', 'Unknown')
        except: sector = 'Unknown'
        
        if mode == "מציאה" and df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 10:
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': 100, 'Sector': sector}
        elif mode == "פריצה" and df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
            score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
            return {'Ticker': ticker, 'Price': round(curr_price, 2), 'StopLoss': stop_loss, 'TakeProfit': take_profit, 'Score': score, 'Sector': sector}
    except: return None
    return None

st.title("🛡️ TITAN: Pro Trading System")
tab1, tab2 = st.tabs(["📉 מציאות", "🚀 פריצות"])

def render_tab(mode, filename):
    if st.button(f"סרוק {mode}"):
        with st.spinner("סורק ומדרג מניות..."):
            results = []
            with ThreadPoolExecutor(max_workers=50) as ex:
                futures = [ex.submit(run_scanner, t, mode) for t in get_universe()]
                for f in futures:
                    res = f.result()
                    if res: results.append(res)
            
            if results:
                df = pd.DataFrame(results).sort_values(by='Score', ascending=False)
                df.to_csv(filename, index=False)
                st.session_state[mode] = df
            else: st.warning("לא נמצאו מניות כרגע.")

    if mode not in st.session_state and os.path.exists(filename):
        if os.path.getsize(filename) > 0:
            st.session_state[mode] = pd.read_csv(filename).sort_values(by='Score', ascending=False)
    
    if mode in st.session_state:
        st.dataframe(st.session_state[mode], use_container_width=True)
        st.download_button(f"📥 הורד אקסל {mode}", data=st.session_state[mode].to_csv(index=False), file_name=f"{mode}.csv")
        if st.button(f"🗑️ נקה {mode}", key=f"clear_{mode}"):
            if os.path.exists(filename): os.remove(filename)
            del st.session_state[mode]
            st.rerun()

with tab1: render_tab("מציאה", "res_val.csv")
with tab2: render_tab("פריצה", "res_brk.csv")
