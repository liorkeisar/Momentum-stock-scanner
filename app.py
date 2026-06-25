import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- הגדרות עמוד ---
st.set_page_config(page_title="KEISAR Stock Wave", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- 1. פונקציות ליבה ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        return yf.Ticker(ticker).history(period="6mo")
    except:
        return pd.DataFrame()

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
    if df is None or len(df) < 20: 
        return -1, "❌ נתונים חסרים (פחות מ-20 ימי מסחר)"
    
    # פילטר נזילות מוסדית
    avg_vol = df['Volume'].mean()
    if avg_vol < 500000:
        return -1, f"❌ פסילה (נזילות): מחזור ממוצע של {int(avg_vol/1000)}K מניות נמוך מדי."
    
    reasons = []
    
    # בדיקות פסילה אסטרטגיות
    if df['Daily_Change'].tail(3).sum() > 0.08:
        return -1, "❌ פסילה: עלייה חדה מדי ב-3 ימים אחרונים (סכנת תיקון)."
    
    dist_from_ma = (df['Close'].iloc[-1] - df['MA20'].iloc[-1]) / df['MA20'].iloc[-1]
    if abs(dist_from_ma) > 0.04:
        return -1, f"❌ פסילה: מחיר רחוק מהממוצע ב-{abs(dist_from_ma)*100:.1f}%."
    
    if df['RSI'].iloc[-1] > 70:
        return -1, "❌ פסילה: מצב קניית יתר (RSI > 70)."
    
    # חישוב ציון והסברים
    score = 4 
    reasons.append("✅ דחיסה (Squeeze) תקינה")
    
    if df['OBV'].diff(5).mean() > 0:
        score += 2
        reasons.append("✅ מומנטום חיובי (OBV)")
    else:
        reasons.append("⚠️ ללא צבירת מוסדיים (OBV)")
        
    if 1.0 < df['RVOL'].iloc[-1] < 1.4:
        score += 1
        reasons.append("✅ ווליום יחסי (RVOL) תקין")
    else:
        reasons.append("⚠️ ווליום לא אידיאלי")
        
    return score, " | ".join(reasons)

def calculate_trade_levels(df):
    price = float(df['Close'].iloc[-1])
    atr = float(df['ATR'].iloc[-1])
    sl = round(price - (1.5 * atr), 2)
    tp = round(price + (3.0 * atr), 2)
    return sl, tp

# --- 2. ממשק משתמש ---
st.title("◈ KEISAR Stock Wave: מערכת ניתוח")
tab1, tab2, tab3, tab4 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי", "🔍 זן מניה"])

with tab1:
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
    selected_files = st.multiselect("בחר רשימות לסריקה:", all_files)
    if st.button("🚀 הפעל סריקה"):
        master_list = []
        for file in selected_files:
            tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
            for t in tickers:
                t = str(t).strip().split(' ')[0]
                df = get_indicators(get_data(t))
                score, reason = calculate_score(df)
                if score >= 0:
                    master_list.append({"Ticker": t, "Score": score, "Price": round(float(df['Close'].iloc[-1]), 2), "Details": reason})
        pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        st.rerun()
    
    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        for _, row in df_res.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{row['Ticker']}** | ציון: {row['Score']} | מחיר: {row['Price']} | {row['Details']}")
            if col2.button("➕ הוסף", key=f"add_scan_{row['Ticker']}"):
                pd.DataFrame({'Ticker': [row['Ticker']], 'Entry': [row['Price']], 'Date': [datetime.now().strftime("%Y-%m-%d")]}).to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success("נוספה לתיק!")

with tab2:
    if os.path.exists(PORTFOLIO_FILE):
        df_p = pd.read_csv(PORTFOLIO_FILE)
        for _, row in df_p.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.write(f"💼 {row['Ticker']} | כניסה: ${row['Entry']} | בתאריך: {row['Date']}")
            if col2.button("❌ הסר", key=f"del_{row['Ticker']}"):
                df_p = df_p[df_p['Ticker'] != row['Ticker']]
                df_p.to_csv(PORTFOLIO_FILE, index=False)
                st.rerun()
    else: st.info("התיק ריק.")

with tab4:
    ticker = st.text_input("הזן מניה לניתוח מהיר:").upper()
    if st.button("בדוק מניה"):
        df = get_indicators(get_data(ticker))
        score, reason = calculate_score(df)
        st.metric("ציון", f"{score}/7" if score >= 0 else "נפסל")
        if score >= 0:
            st.write(reason)
            sl, tp = calculate_trade_levels(df)
            st.write(f"🎯 **יעדי עסקה:** Stop Loss: ${sl} | Take Profit: ${tp}")
            if st.button("➕ הוסף לתיק", key="add_fast"):
                pd.DataFrame({'Ticker': [ticker], 'Entry': [float(df['Close'].iloc[-1])], 'Date': [datetime.now().strftime("%Y-%m-%d")]}).to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success("נוספה!")
        else: st.error(reason)

with tab3:
    st.header("🎓 אסטרטגיית צייד התפרצויות (ASST)")
    st.markdown("""
    המערכת מחפשת דחיסה (Squeeze) המצביעה על אנרגיה טכנית צבורה לפני מהלך.
    **כללי הברזל:** 1. דחיסה, 2. מומנטום חיובי, 3. אישור ווליום.
    """)
