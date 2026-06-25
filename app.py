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
    try:
        return yf.Ticker(ticker).history(period="6mo")
    except:
        return pd.DataFrame()

def get_market_cap(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('marketCap', 0)
    except:
        return 0

def get_indicators(df):
    if df.empty or len(df) < 30: return None
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
        if df['Daily_Change'].tail(3).sum() > 0.08 or abs(dist_from_ma) > 0.04 or df['RSI'].iloc[-1] > 70:
            return -1
        min_squeeze = df['Squeeze'].rolling(20).min().iloc[-1]
        if df['Squeeze'].iloc[-1] > min_squeeze * 1.05:
            return -1
        is_squeezing = df['Squeeze'] < df['Squeeze'].rolling(20).mean()
        if is_squeezing.rolling(5).sum().iloc[-1] < 5:
            return -1
        score = 4
        if df['OBV'].diff(5).mean() > 0: score += 2
        if 1.0 < df['RVOL'].iloc[-1] < 1.4: score += 1
        return score
    except: return -1

def calculate_trade_levels(df):
    price = float(df['Close'].iloc[-1])
    atr = float(df['ATR'].iloc[-1])
    sl = round(price - (2 * atr), 2)
    tp = round(price + (4 * atr), 2)
    return price, sl, tp

# --- 2. ממשק משתמש ---
st.title("◈ KEISAR Pro Hunter: מערכת ניתוח מתקדמת")
tab1, tab2, tab3, tab4 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי", "🔍 זן מניה"])

with tab1:
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
    selected_files = st.multiselect("בחר רשימות לסריקה:", all_files)
    if st.button("🚀 הפעל סריקה"):
        master_list = []
        with st.spinner("סורק שוק..."):
            for file in selected_files:
                try:
                    tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
                    for t in tickers:
                        # שונה ל-300,000,000
                        if get_market_cap(t) > 300_000_000:
                            df = get_indicators(get_data(t))
                            score = calculate_score(df)
                            if score >= 0:
                                master_list.append({"Ticker": t, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2)})
                except Exception as e:
                    st.error(f"שגיאה בקובץ {file}: {e}")
        
        # --- תיקון יציבות: הגנה לפני מיון ושמירה ---
        if master_list:
            df_final = pd.DataFrame(master_list)
            if 'Score' in df_final.columns:
                df_final = df_final.sort_values(by="Score", ascending=False)
            df_final.to_csv(SCAN_RESULTS_FILE, index=False)
            st.rerun()
        else:
            if os.path.exists(SCAN_RESULTS_FILE):
                os.remove(SCAN_RESULTS_FILE)
            st.warning("לא נמצאו מניות העומדות בקריטריונים בסריקה זו.")

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        st.dataframe(df_res, use_container_width=True)

with tab4:
    ticker = st.text_input("הזן מניה לניתוח מהיר:").upper()
    if st.button("בדוק מניה"):
        df = get_indicators(get_data(ticker))
        score = calculate_score(df)
        if score >= 0:
            price, sl, tp = calculate_trade_levels(df)
            st.metric("ציון אסטרטגי", f"{score}/7")
            st.info(f"🎯 **ניהול עסקה מומלץ:**\n\nכניסה: **${price}** | יעד (TP): **${tp}** | עצירת הפסד (SL): **${sl}**")
            
            if st.button("➕ הוסף לתיק"):
                if os.path.exists(PORTFOLIO_FILE):
                    port = pd.read_csv(PORTFOLIO_FILE)
                    if ticker in port['Ticker'].values:
                        st.warning("המניה כבר קיימת בתיק!")
                    else:
                        pd.DataFrame({'Ticker': [ticker], 'Entry': [price], 'Date': [datetime.now().strftime("%Y-%m-%d")]}).to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
                        st.success("נוספה לתיק!")
                else:
                    pd.DataFrame({'Ticker': [ticker], 'Entry': [price], 'Date': [datetime.now().strftime("%Y-%m-%d")]}).to_csv(PORTFOLIO_FILE, index=False)
                    st.success("נוספה לתיק!")

with tab3:
    st.header("🎓 אסטרטגיית צייד התפרצויות")
    st.write("המערכת מסננת מניות בעלות שווי שוק מעל 300M$ שנמצאות בתהליך דחיסה טכנית.")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        st.table(pd.read_csv(PORTFOLIO_FILE))
