import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np
import smtplib
from email.message import EmailMessage

# --- הגדרות ---
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'
MIN_VOLUME = 500000 
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password" 
EMAIL_RECEIVER = "your_email@gmail.com"

# --- פונקציות טכניות ---
def get_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze_Width'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    return df.dropna()

def calculate_squeeze_score(df):
    squeeze_days = 0
    for width in reversed(df['Squeeze_Width'].tail(30)):
        if width < 0.15: squeeze_days += 1
        else: break
    return squeeze_days

# --- ממשק ---
st.set_page_config(page_title="KEISAR Pro", layout="wide")

# --- צד - בחירת רשימות מניות ---
st.sidebar.header("📂 בחירת רשימות מניות")
# סריקת קבצי CSV בתיקייה הנוכחית
csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and f not in [PORTFOLIO_FILE, SCAN_RESULTS_FILE]]
selected_files = st.sidebar.multiselect("סמן את הרשימות לסריקה:", csv_files, default=csv_files)

st.title("◈ KEISAR: סורק מוסדי")

tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    if st.button("🚀 הפעל סריקה"):
        if not selected_files:
            st.error("לא נבחרו קבצי רשימות. בחר מהתפריט בצד.")
        else:
            master_list = []
            progress_bar = st.progress(0)
            for i, file in enumerate(selected_files):
                tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
                for ticker in tickers:
                    try:
                        df = yf.Ticker(ticker).history(period="6mo")
                        if len(df) > 50 and df['Volume'].tail(20).mean() > MIN_VOLUME:
                            df = get_indicators(df)
                            if not df.empty and df['Squeeze_Width'].iloc[-1] < 0.15:
                                master_list.append({
                                    "Ticker": ticker, 
                                    "Price": round(float(df['Close'].iloc[-1]), 2), 
                                    "Squeeze": round(df['Squeeze_Width'].iloc[-1], 3), 
                                    "Duration_Days": calculate_squeeze_score(df)
                                })
                    except: continue
                progress_bar.progress((i + 1) / len(selected_files))
            pd.DataFrame(master_list).to_csv(SCAN_RESULTS_FILE, index=False)
            st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        if not df_res.empty:
            if "Duration_Days" in df_res.columns:
                df_res = df_res.sort_values(by="Duration_Days", ascending=False)
            st.dataframe(df_res, use_container_width=True)
            
            selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
            if st.button("הצג גרפים"):
                data = get_indicators(yf.Ticker(selected).history(period="6mo"))
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['OBV'], name='OBV', line=dict(color='blue')), row=2, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD', line=dict(color='red')), row=3, col=1)
                st.plotly_chart(fig, use_container_width=True)
        else: st.info("לא נמצאו מניות בתנאי הסריקה.")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.dataframe(pd.read_csv(PORTFOLIO_FILE, names=['Ticker']))

with tab3:
    st.header("🎓 מדריך אסטרטגי")
    st.markdown("האסטרטגיה מתבססת על זיהוי **דחיסה טכנית (Squeeze)** שמצביעה על אגירת אנרגיה לפני מהלך גדול.")
    st.markdown("---")
    st.columns(2)[0].markdown("**איסוף מוסדי (Wyckoff):**")
    [attachment_0](attachment)
