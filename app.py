import streamlit as st
import yfinance as yf
import pandas as pd
import os

# הגדרת דף
st.set_page_config(page_title="סורק וייקוף Pro", layout="wide")
st.title("◈ סורק מניות מוסדי - Wyckoff Pro")

# --- פונקציות עזר ---
def get_available_lists():
    return [f for f in os.listdir('.') if f.endswith('.csv')]

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    # זיהוי עמודה חכם
    cols = ['Symbol', 'Ticker', 'Symbol ', 'TICKER', 'Symbol (NASDAQ)']
    target = next((c for c in cols if c in df.columns), df.columns[0])
    return df[target].dropna().astype(str).tolist()

def calculate_wyckoff_score(df):
    if df is None or len(df) < 20: return 0, 0, 0
    recent = df.tail(20)
    up = recent[recent['Close'] >= recent['Close'].shift(1)]
    down = recent[recent['Close'] < recent['Close'].shift(1)]
    
    vr = (up['Volume'].mean() / down['Volume'].mean()) if down['Volume'].mean() > 0 else 1
    rw = (recent['High'].max() - recent['Low'].min()) / ((recent['High'].max() + recent['Low'].min()) / 2) * 100
    
    score = (40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0)
    return min(score, 100), vr, rw

# --- ממשק משתמש ---
available_lists = get_available_lists()
selected_file = st.sidebar.selectbox("בחר רשימה:", available_lists)
min_score = st.sidebar.slider("סנן מניות עם ציון מינימלי:", 0, 100, 40)
manual_ticker = st.sidebar.text_input("הזן טיקר ידני (ולחץ Enter):").upper().strip()

if st.sidebar.button("הרץ סריקה"):
    # ניקוי תוצאות קודמות
    st.session_state['results_df'] = None
    
    # בניית רשימה מאוחדת
    tickers = [manual_ticker] if manual_ticker else []
    tickers.extend([t for t in load_selected_list(selected_file) if t not in tickers])
    
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(tickers[:50]): # סריקת 50 מניות למניעת עומס
        try:
            df = yf.Ticker(ticker).history(period="3mo")
            if not df.empty:
                score, vr, rw = calculate_wyckoff_score(df)
                tv_link = f"https://www.tradingview.com/chart/?symbol={ticker}"
                results.append({"Ticker": ticker, "Score": score, "VR": round(vr, 2), "RW": round(rw, 2), "Chart": tv_link})
        except: continue
        progress_bar.progress((i + 1) / 50)
    
    st.session_state['results_df'] = pd.DataFrame(results)
    st.rerun()

# --- תצוגה ---
if st.session_state.get('results_df') is not None:
    df = st.session_state['results_df']
    df = df[df['Score'] >= min_score] # סינון דינמי לפי ה-Slider
    st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)
