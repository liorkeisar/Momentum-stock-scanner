import streamlit as st
import yfinance as yf
import pandas as pd
import os
import numpy as np
from datetime import datetime

# --- הגדרות עמוד ---
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- 1. פונקציות ליבה ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try: return yf.Ticker(ticker).history(period="6mo")
    except: return pd.DataFrame()

def get_market_cap(ticker):
    try: return yf.Ticker(ticker).info.get('marketCap', 0)
    except: return 0

def get_indicators(df):
    if df.empty or len(df) < 30: return None
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['AvgVol'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['AvgVol']
    df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    return df.fillna(0)

def calculate_score(df):
    if df is None: return -1
    try:
        dist_from_ma = (df['Close'].iloc[-1] - df['MA20'].iloc[-1]) / df['MA20'].iloc[-1]
        if abs(dist_from_ma) > 0.04 or df['RSI'].iloc[-1] > 70: return -1
        score = 4
        if df['OBV'].diff(5).mean() > 0: score += 2
        if 1.0 < df['RVOL'].iloc[-1] < 1.4: score += 1
        return score
    except: return -1

def add_to_portfolio(ticker, price):
    hist = yf.Ticker(ticker).history(period="1mo")
    atr = float(hist['High'].iloc[-1] - hist['Low'].iloc[-1])
    sl = round(price - (2 * atr), 2)
    tp = round(price + (4 * atr), 2)
    
    rr = round((tp - price) / (price - sl), 2)
    risk_pct = round(((price - sl) / price) * 100, 2)
    reward_pct = round(((tp - price) / price) * 100, 2)
    
    new_data = pd.DataFrame({
        'Ticker': [ticker], 'Entry': [price], 'SL': [sl], 'TP': [tp], 
        'R:R': [rr], 'Risk%': [risk_pct], 'Reward%': [reward_pct], 'Date': [datetime.now().strftime("%Y-%m-%d")]
    })
    
    if os.path.exists(PORTFOLIO_FILE):
        port = pd.read_csv(PORTFOLIO_FILE)
        if ticker in port['Ticker'].values: return False, "המניה כבר קיימת בתיק"
        new_data.to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
    else:
        new_data.to_csv(PORTFOLIO_FILE, index=False)
    return True, "נוספה בהצלחה"

# --- 2. ממשק משתמש ---
st.title("◈ KEISAR Pro Hunter: מערכת סריקה מלאה")
tab1, tab2, tab3, tab4 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 אסטרטגיה", "🔍 זן מניה"])

with tab1:
    # זיהוי אוטומטי של כל קבצי ה-CSV בתיקייה (למעט קבצי המערכת)
    all_csv = [f for f in os.listdir('.') if f.endswith('.csv') and f not in [PORTFOLIO_FILE, SCAN_RESULTS_FILE]]
    selected = st.multiselect("בחר רשימות לסריקה:", all_csv, default=all_csv)
    
    if st.button("🚀 הפעל סריקה מלאה"):
        master = []
        progress_bar = st.progress(0)
        with st.spinner("סורק מניות..."):
            for i, file in enumerate(selected):
                tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
                for t in tickers:
                    if get_market_cap(t) > 350_000_000:
                        df = get_indicators(get_data(t))
                        score = calculate_score(df)
                        if score >= 0:
                            master.append({"Ticker": t, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2)})
                progress_bar.progress((i + 1) / len(selected))
        
        pd.DataFrame(master).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()
    
    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, use_container_width=True)
        sel = st.selectbox("בחר מניה לביצוע פעולה:", df_res['Ticker'].unique() if not df_res.empty else [])
        if sel and st.button("➕ הוסף לתיק"):
            price = df_res[df_res['Ticker'] == sel]['Price'].iloc[0]
            succ, msg = add_to_portfolio(sel, price)
            if succ: st.success(msg)
            else: st.warning(msg)

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_port = pd.read_csv(PORTFOLIO_FILE)
        def highlight_rr(val):
            color = 'lightgreen' if val >= 2 else 'lightcoral'
            return f'background-color: {color}'
        st.subheader("תיק עסקאות פעיל")
        st.dataframe(df_port.style.applymap(highlight_rr, subset=['R:R']), use_container_width=True)
    else:
        st.info("התיק ריק.")

with tab3:
    st.header("🎓 אסטרטגיית צייד התפרצויות (ASST)")
    st.write("מערכת סריקה לזיהוי התפרצויות טכניות מבוססת דחיסות, ווליום ומומנטום.")

with tab4:
    ticker = st.text_input("הזן מניה לניתוח מהיר:").upper()
    if st.button("בדוק מניה"):
        df = get_indicators(get_data(ticker))
        score = calculate_score(df)
        if score >= 0:
            price = float(df['Close'].iloc[-1])
            st.metric("ציון אסטרטגי", f"{score}/7")
            if st.button("➕ הוסף לתיק"):
                succ, msg = add_to_portfolio(ticker, price)
                if succ: st.success(msg)
                else: st.warning(msg)
        else:
            st.error("לא עומדת בתנאי האסטרטגיה או שווי שוק נמוך מ-350M$.")
