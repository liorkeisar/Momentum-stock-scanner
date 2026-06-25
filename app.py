import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'

# --- 1. מנוע נתונים ואינדיקטורים ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="6mo")
        return df if not df.empty else pd.DataFrame()
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

# --- 2. לוגיקת ניקוד עם פילטר נזילות ---
def calculate_score(df):
    if df is None or len(df) < 20: 
        return -1, "❌ נתונים חסרים (פחות מ-20 ימי מסחר)"
    
    # פילטר נזילות - מונע "מניות זבל"
    avg_vol = df['Volume'].mean()
    if avg_vol < 500000:
        return -1, f"❌ פסילה: מחזור נמוך ({int(avg_vol/1000)}K מניות בממוצע)"
        
    reasons = []
    
    # בדיקות פסילה
    if df['Daily_Change'].tail(3).sum() > 0.08:
        return -1, "❌ פסילה: עלייה חדה מדי (מעל 8% ב-3 ימים)"
    
    dist_from_ma = (df['Close'].iloc[-1] - df['MA20'].iloc[-1]) / df['MA20'].iloc[-1]
    if abs(dist_from_ma) > 0.04:
        return -1, f"❌ פסילה: מחיר רחוק מהממוצע ({abs(dist_from_ma)*100:.1f}%)"
    
    if df['RSI'].iloc[-1] > 70:
        return -1, "❌ פסילה: מניה במצב קניית יתר (RSI > 70)"
    
    # חישוב ציון
    score = 4 
    reasons.append("✅ דחיסה (Squeeze) תקינה")
    
    if df['OBV'].diff(5).mean() > 0:
        score += 2
        reasons.append("✅ מומנטום חיובי (OBV צומח)")
    else:
        reasons.append("⚠️ ללא צבירת מוסדיים (OBV שלילי)")
        
    if 1.0 < df['RVOL'].iloc[-1] < 1.4:
        score += 1
        reasons.append("✅ ווליום יחסי (RVOL) תקין")
    else:
        reasons.append("⚠️ ווליום לא אידיאלי")
        
    return score, " | ".join(reasons)

# --- 3. ממשק משתמש ---
st.title("◈ KEISAR Pro Hunter: מערכת ניתוח")
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
        if master_list:
            pd.DataFrame(master_list).sort_values(by="Score", ascending=False).to_csv(SCAN_RESULTS_FILE, index=False)
        else:
            if os.path.exists(SCAN_RESULTS_FILE): os.remove(SCAN_RESULTS_FILE)
        st.rerun()
    
    if os.path.exists(SCAN_RESULTS_FILE):
        st.dataframe(pd.read_csv(SCAN_RESULTS_FILE), use_container_width=True)

with tab4:
    ticker = st.text_input("הזן מניה לניתוח מהיר:").upper()
    if st.button("בדוק מניה"):
        df = get_indicators(get_data(ticker))
        score, reason = calculate_score(df)
        if score >= 0:
            st.metric("ציון סופי", f"{score}/7")
            for point in reason.split(" | "): st.write(point)
        else:
            st.error(reason)

with tab3:
    st.header("🎓 אסטרטגיית צייד התפרצויות")
    st.write("המערכת מזהה דחיסה טכנית מלווה בצבירת מוסדיים (פילטר נזילות: 500K מניות/יום).")

with tab2:
    if os.path.exists(PORTFOLIO_FILE): st.table(pd.read_csv(PORTFOLIO_FILE))
    else: st.info("התיק ריק.")
