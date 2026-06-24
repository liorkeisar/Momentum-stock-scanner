import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np

# הגדרות עמוד
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- פונקציות עזר (לוגיקה) ---

@st.cache_data(ttl=3600)
def get_data(ticker):
    """משיכת נתונים עם Caching לשיפור ביצועים"""
    return yf.Ticker(ticker).history(period="6mo")

def get_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    # תיקון: Squeeze מחושב כאחוז מהמחיר
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

def calculate_score(df):
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2  # משקל גבוה לדחיסה חזקה
    elif df['Squeeze'].iloc[-1] < 0.15: score += 1
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]: score += 1
    if df['MACD'].iloc[-1] > df['Signal'].iloc[-1]: score += 1
    return score

# --- ממשק משתמש ---

st.sidebar.header("⚙️ הגדרות סריקה")
all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
selected_files = st.sidebar.multiselect("בחר קבצי רשימות (Tickers):", all_files, default=all_files)

if st.sidebar.button("🗑️ נקה תוצאות סריקה"):
    if os.path.exists(SCAN_RESULTS_FILE): os.remove(SCAN_RESULTS_FILE)
    st.rerun()

st.title("◈ KEISAR: סורק מוסדי מקצועי")
tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    if st.button("🚀 הפעל סריקה"):
        master_list = []
        progress_bar = st.progress(0)
        
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(pd.read_csv(file, header=None).iloc[:, 0].dropna().unique())
        
        for i, ticker in enumerate(all_tickers):
            try:
                df = get_indicators(get_data(ticker))
                if len(df) > 50:
                    score = calculate_score(df)
                    master_list.append({
                        "Ticker": ticker, "Score": score, 
                        "Price": round(float(df['Close'].iloc[-1]), 2), 
                        "Squeeze": round(df['Squeeze'].iloc[-1], 3)
                    })
            except Exception: continue
            progress_bar.progress((i + 1) / len(all_tickers))
        
        if master_list:
            pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, use_container_width=True)
        
        selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
        if st.button("הצג ניתוח טכני"):
            data = get_indicators(get_data(selected))
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Upper'], line=dict(color='gray', dash='dash'), name='Bollinger'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Lower'], line=dict(color='gray', dash='dash'), showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['OBV'], name='OBV', line=dict(color='blue')), row=2, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("הוסף לתיק"):
                if os.path.exists(PORTFOLIO_FILE):
                    port = pd.read_csv(PORTFOLIO_FILE, names=['Ticker'])
                    if selected in port['Ticker'].values:
                        st.warning("המניה כבר קיימת בתיק!")
                    else:
                        pd.DataFrame({'Ticker': [selected]}).to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
                        st.success(f"{selected} נוספה!")
                else:
                    pd.DataFrame({'Ticker': [selected]}).to_csv(PORTFOLIO_FILE, index=False, header=False)
                    st.success(f"{selected} נוספה!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.dataframe(pd.read_csv(PORTFOLIO_FILE, names=['Ticker']), use_container_width=True)
    else:
        st.info("התיק ריק.")

with tab3:
    st.header("🎓 מדריך אסטרטגי: צייד התפרצויות")
    st.markdown("האסטרטגיה מבוססת על **Bollinger Squeeze** - רגיעה לפני סערה.")
    # 
    st.info("ככל שה-Squeeze נמוך יותר, כך פוטנציאל הפריצה גבוה יותר.")
