import streamlit as st
import yfinance as yf
import pandas as pd
import time
import os

st.set_page_config(page_title="סורק וייקוף מוסדי", layout="wide")
st.title("◈ סורק מניות מוסדי - Wyckoff Accumulation")

# --- פונקציות עזר ---
def get_available_lists():
    return [f for f in os.listdir('.') if f.endswith('.csv')]

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    # מנגנון חכם: מחפש עמודה שנשמעת כמו סימבול
    possible_cols = ['Symbol', 'Ticker', 'Symbol ', 'TICKER']
    target_col = next((col for col in possible_cols if col in df.columns), df.columns[0])
    
    st.sidebar.write(f"משתמש בעמודה: {target_col}")
    return df[target_col].dropna().astype(str).tolist()

def calculate_wyckoff_score(df):
    if len(df) < 20: return 0, 0, 0
    recent = df.tail(20)
    down = recent[recent['Close'] < recent['Close'].shift(1)]
    up = recent[recent['Close'] >= recent['Close'].shift(1)]
    avg_vol_down = down['Volume'].mean() if len(down) > 0 else 1
    avg_vol_up = up['Volume'].mean() if len(up) > 0 else 1
    vol_ratio = avg_vol_up / avg_vol_down if avg_vol_down != 0 else 1
    hi, lo = recent['High'].max(), recent['Low'].min()
    rw = (hi - lo) / ((hi + lo) / 2) * 100
    score = 0
    if vol_ratio > 1.2: score += 40
    if rw < 7: score += 40
    if rw < 4: score += 20
    return min(score, 100), vol_ratio, rw

# --- ממשק משתמש ---
if 'results_df' not in st.session_state: st.session_state['results_df'] = None

available_lists = get_available_lists()
selected_file = st.sidebar.selectbox("בחר רשימת מניות:", available_lists)
manual_ticker = st.sidebar.text_input("הזן טיקר ידני (למשל: MSFT):").upper()

if st.sidebar.button("הרץ סריקה"):
    tickers = load_selected_list(selected_file)
    if manual_ticker: tickers.append(manual_ticker)
    
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(tickers[:100]):
        try:
            df = yf.Ticker(ticker.strip()).history(period="3mo")
            score, vr, rw = calculate_wyckoff_score(df)
            results.append({"Ticker": ticker, "Score": score, "VR": round(vr, 2), "RW": round(rw, 2)})
            progress_bar.progress((i + 1) / 100)
        except: continue
    
    st.session_state['results_df'] = pd.DataFrame(results)
    st.rerun()

if st.session_state['results_df'] is not None:
    st.dataframe(st.session_state['results_df'].sort_values("Score", ascending=False), use_container_width=True)
