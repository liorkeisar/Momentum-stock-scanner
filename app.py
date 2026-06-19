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
MIN_VOLUME = 500000  # סעיף 3: מסנן נזילות
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password" 
EMAIL_RECEIVER = "your_email@gmail.com"

# --- פונקציות עזר ---
def send_email(ticker):
    msg = EmailMessage()
    msg.set_content(f"מניה חדשה נכנסה לאזור לחץ (Squeeze): {ticker}. בדוק OBV בגרף!")
    msg['Subject'] = f"KEISAR Alert: {ticker}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except: pass

def get_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze_Width'] = (df['Upper'] - df['Lower']) / df['Close']
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# סעיף 2: חישוב עוצמת דחיסה היסטורית
def calculate_squeeze_score(df):
    squeeze_days = 0
    for width in reversed(df['Squeeze_Width'].tail(30)):
        if width < 0.15: squeeze_days += 1
        else: break
    return squeeze_days

# --- ממשק ---
st.set_page_config(page_title="KEISAR Pro", layout="wide")
st.title("◈ KEISAR: סורק מוסדי מקצועי")

tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    if st.button("🚀 הפעל סריקה"):
        master_list = []
        progress_bar = st.progress(0)
        # בחירת תיקיות מהצד
        all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
        
        for i, file in enumerate(all_files):
            tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
            for ticker in tickers:
                try:
                    df = yf.Ticker(ticker).history(period="6mo")
                    # סעיף 3: בדיקת נזילות
                    avg_vol = df['Volume'].tail(20).mean()
                    if len(df) > 50 and avg_vol > MIN_VOLUME:
                        df = get_indicators(df)
                        if df['Squeeze_Width'].iloc[-1] < 0.15:
                            duration = calculate_squeeze_score(df)
                            master_list.append({
                                "Ticker": ticker, 
                                "Price": round(float(df['Close'].iloc[-1]), 2), 
                                "Squeeze": round(df['Squeeze_Width'].iloc[-1], 3),
                                "Duration_Days": duration
                            })
                            # סעיף 1: התראה למייל
                            if duration == 1: send_email(ticker)
                except: continue
            progress_bar.progress((i + 1) / len(all_files))
        pd.DataFrame(master_list).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE).sort_values(by="Duration_Days", ascending=False)
        st.dataframe(df_res, use_container_width=True)
        # [קוד הצגת גרפים...]

with tab3:
    st.header("🎓 מדריך אסטרטגי: צייד התפרצויות")
    st.markdown("כדי להבין לעומק את המנגנונים הטכניים של דחיסה והתכנסות, מומלץ לעיין בהסברים הבאים:")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**התכנסות (Bollinger Squeeze):**")
        
    with col2:
        st.markdown("**צבירת סחורה (OBV):**")
        [attachment_0](attachment)
