import streamlit as st
import yfinance as yf
import pandas as pd
import time
import os

# הגדרות עמוד
st.set_page_config(page_title="סורק וייקוף מוסדי", layout="wide")
st.title("◈ סורק מניות מוסדי - Wyckoff Accumulation")

# --- פונקציות עזר ---
def get_available_lists():
    return [f for f in os.listdir('.') if f.endswith('.csv')]

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    # זיהוי אוטומטי של עמודת הסימבולים
    possible_cols = ['Symbol', 'Ticker', 'Symbol ', 'TICKER']
    target_col = next((col for col in possible_cols if col in df.columns), df.columns[0])
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
manual_ticker = st.sidebar.text_input("הזן טיקר ידנית (למשל: MSFT):").upper()

if st.sidebar.button("הרץ סריקה"):
    tickers_from_file = load_selected_list(selected_file)
    
    # בניית רשימת סריקה מאוחדת (ידני ראשון)
    all_tickers = []
    if manual_ticker:
        all_tickers.append(manual_ticker.strip())
    
    for t in tickers_from_file:
        clean_t = str(t).strip()
        if clean_t not in all_tickers:
            all_tickers.append(clean_t)
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.sidebar.empty()
    
    # סריקה מוגבלת ל-50 מניות לטובת יציבות
    for i, ticker in enumerate(all_tickers[:50]):
        try:
            status_text.text(f"סורק: {ticker}")
            df = yf.Ticker(ticker).history(period="3mo")
            if df.empty: continue
            
            score, vr, rw = calculate_wyckoff_score(df)
            results.append({"Ticker": ticker, "Score": score, "VR": round(vr, 2), "RW": round(rw, 2)})
            progress_bar.progress((i + 1) / 50)
        except Exception:
            continue
    
    st.session_state['results_df'] = pd.DataFrame(results)
    st.rerun()

# --- תצוגה ---
if st.session_state['results_df'] is not None:
    st.subheader("תוצאות הסריקה")
    # הצגת טבלה ממוינת לפי ציון
    df_results = st.session_state['results_df'].sort_values("Score", ascending=False)
    st.dataframe(df_results, use_container_width=True)
    
    # הורדה ל-CSV
    st.download_button("📥 הורד תוצאות ל-CSV", 
                       data=df_results.to_csv(index=False), 
                       file_name='scan_results.csv')
