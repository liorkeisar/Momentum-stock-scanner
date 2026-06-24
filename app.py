import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np
from datetime import datetime

# הגדרות כלליות
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- פונקציות חישוב ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    return yf.Ticker(ticker).history(period="6mo")

def get_indicators(df):
    df = df.copy()
    df['Daily_Change'] = df['Close'].pct_change()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['AvgVol'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['AvgVol']
    df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    return df.dropna()

def calculate_score(df):
    if df['Daily_Change'].iloc[-1] < -0.05: return -1
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2
    elif df['Squeeze'].iloc[-1] < 0.15: score += 1
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['RVOL'].iloc[-1] > 1.5: score += 1
    return score

# --- ממשק משתמש ---
st.title("◈ KEISAR: סורק מוסדי מקצועי")
tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    st.sidebar.header("⚙️ הגדרות סריקה")
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f])
    selected_files = st.sidebar.multiselect("בחר קבצי רשימות:", all_files)

    if st.button("🚀 הפעל סריקה"):
        master_list = []
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(pd.read_csv(file, header=None).iloc[:, 0].dropna().unique())
        
        for ticker in all_tickers:
            try:
                df = get_indicators(get_data(ticker))
                score = calculate_score(df)
                if score >= 0:
                    master_list.append({"Ticker": ticker, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), "RVOL": round(float(df['RVOL'].iloc[-1]), 2)})
            except: continue
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, use_container_width=True)
        
        selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג ניתוח"):
            st.session_state['selected_ticker'] = selected
            st.rerun()
            
        if 'selected_ticker' in st.session_state:
            ticker = st.session_state['selected_ticker']
            data = get_indicators(get_data(ticker))
            last_price = float(data['Close'].iloc[-1])
            atr = float(data['ATR'].iloc[-1])
            sl = round(last_price - (1.5 * atr), 2)
            tp = round(last_price + (3.0 * atr), 2)
            rr = round((tp - last_price) / (last_price - sl), 2) if (last_price - sl) != 0 else 0
            
            st.markdown(f"### 📊 ניתוח: {ticker}")
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; background: #f0f2f6; padding: 15px; border-radius: 10px;">
                <div><b>מחיר:</b> ${last_price:.2f}</div>
                <div style="color:red"><b>SL:</b> ${sl}</div>
                <div style="color:green"><b>TP:</b> ${tp}</div>
                <div><b>R/R:</b> 1:{rr}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("הוסף לתיק"):
                new_entry = pd.DataFrame({'Ticker': [ticker], 'Entry': [last_price], 'SL': [sl], 'TP': [tp]})
                mode = 'a' if os.path.exists(PORTFOLIO_FILE) else 'w'
                new_entry.to_csv(PORTFOLIO_FILE, mode=mode, header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success("נוסף לתיק!")
                st.rerun()

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_port = pd.read_csv(PORTFOLIO_FILE)
        # בדיקת תקינות עמודות
        required_cols = ['Ticker', 'Entry', 'SL', 'TP']
        if all(col in df_port.columns for col in required_cols):
            for i, row in df_port.iterrows():
                col1, col2 = st.columns([0.8, 0.2])
                try:
                    curr_p = float(get_data(row['Ticker'])['Close'].iloc[-1])
                    ret = ((curr_p - row['Entry']) / row['Entry']) * 100
                    col1.write(f"**{row['Ticker']}** | כניסה: ${row['Entry']} | נוכחי: ${curr_p:.2f} | תשואה: {ret:.2f}%")
                    col1.caption(f"יעדים: SL ${row['SL']} | TP ${row['TP']}")
                except: col1.write(f"שגיאה בטעינת {row['Ticker']}")
                
                if col2.button("🗑️ הסר", key=f"del_{i}"):
                    df_port.drop(i, inplace=True)
                    df_port.to_csv(PORTFOLIO_FILE, index=False)
                    st.rerun()
        else:
            st.warning("פורמט התיק ישן. אנא מחק את portfolio.csv והוסף מניות מחדש.")
    else:
        st.info("התיק ריק.")
