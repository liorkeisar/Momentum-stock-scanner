import streamlit as st
import yfinance as yf
import pandas as pd
import time
import os

st.set_page_config(page_title="סורק וייקוף מוסדי", layout="wide")
st.title("◈ סורק מניות מוסדי - Wyckoff Accumulation")

# --- פונקציות עזר ---
def get_available_lists():
    return [f for f in os.listdir('.') if f.endswith('.csv') and f != 'nasdaq_screener.csv']

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    return df['Symbol'].dropna().tolist()

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
if 'watchlist' not in st.session_state: st.session_state['watchlist'] = []

# בחירת רשימה
available_lists = get_available_lists()
selected_file = st.sidebar.selectbox("בחר רשימת מניות לסריקה:", available_lists)
manual_ticker = st.sidebar.text_input("הזן טיקר ידנית (למשל: MSFT):").upper()

if st.sidebar.button("הרץ סריקה"):
    tickers_to_scan = load_selected_list(selected_file)
    if manual_ticker: tickers_to_scan.append(manual_ticker)
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.sidebar.empty()
    
    for i, ticker in enumerate(tickers_to_scan[:100]): # הגבלה ל-100 לביצועים
        try:
            status_text.text(f"סורק: {ticker}")
            time.sleep(0.1)
            df = yf.Ticker(ticker).history(period="3mo")
            score, vr, rw = calculate_wyckoff_score(df)
            results.append({"Ticker": ticker, "Wyckoff_Score": score, "Vol_Ratio": round(vr, 2), "Range_Width": round(rw, 2)})
            progress_bar.progress((i + 1) / len(tickers_to_scan[:100]))
        except: continue
    
    st.session_state['results_df'] = pd.DataFrame(results)
    status_text.text("הסריקה הושלמה!")

# --- תצוגה ---
if st.session_state['results_df'] is not None:
    st.subheader("תוצאות הסריקה")
    df = st.session_state['results_df'].sort_values("Wyckoff_Score", ascending=False)
    st.dataframe(df, use_container_width=True)
    
    watchlist = st.multiselect("בחר מועדפים:", df['Ticker'].tolist(), default=st.session_state['watchlist'])
    st.session_state['watchlist'] = watchlist
    
    if watchlist:
        st.download_button("📥 הורד מועדפים ל-Google Sheets", 
                           data=df[df['Ticker'].isin(watchlist)].to_csv(index=False), 
                           file_name='watchlist.csv')
