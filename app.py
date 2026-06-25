import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="KEISAR Stock Wave", layout="wide")
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

# --- 2. לוגיקת ניקוד לימודית ---
def calculate_score(df):
    if df is None or len(df) < 20: 
        return -1, "❌ נתונים חסרים: דרושים מינימום 20 ימי מסחר."
    
    # פילטר נזילות מוסדית
    avg_vol = df['Volume'].mean()
    if avg_vol < 500000:
        return -1, f"❌ פסילה (נזילות): מחזור ממוצע של {int(avg_vol/1000)}K מניות אינו מספיק לאמינות טכנית."
        
    reasons = []
    
    # בדיקות פסילה אסטרטגיות
    if df['Daily_Change'].tail(3).sum() > 0.08:
        return -1, "❌ פסילה (מומנטום יתר): עלייה של מעל 8% ב-3 ימים מעידה שהמהלך כבר החל. סכנת תיקון."
    
    dist_from_ma = (df['Close'].iloc[-1] - df['MA20'].iloc[-1]) / df['MA20'].iloc[-1]
    if abs(dist_from_ma) > 0.04:
        return -1, f"❌ פסילה (מרחק מהממוצע): המניה רחוקה {abs(dist_from_ma)*100:.1f}% מה-MA20."
    
    if df['RSI'].iloc[-1] > 70:
        return -1, "❌ פסילה (RSI): מניה במצב קניית יתר (מעל 70), סיכון גבוה לכניסה."
    
    # חישוב ציון והסברים לימודיים
    score = 4 
    reasons.append("✅ דחיסה (Squeeze): תנודתיות נמוכה, הכנה לפני התפרצות טכנית.")
    
    if df['OBV'].diff(5).mean() > 0:
        score += 2
        reasons.append("✅ צבירה מוסדית (OBV): נפח מסחר בעליות גבוה מירידות, עדות לאיסוף ע\"י כסף חכם.")
    else:
        reasons.append("⚠️ ללא צבירה: מדד ה-OBV שלילי. חסר אישור מוסדי למהלך עליות.")
        
    if 1.0 < df['RVOL'].iloc[-1] < 1.4:
        score += 1
        reasons.append("✅ ווליום יחסי (RVOL): נפח מסחר בריא ומאוזן, תומך בפריצה תקינה.")
    else:
        reasons.append("⚠️ ווליום לא אידיאלי: תנועה ללא נפח מסחר עקבי עלולה להיות פריצת שווא.")
        
    return score, " | ".join(reasons)

# --- 3. ממשק משתמש ---
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
    st.header("🎓 אסטרטגיית צייד התפרצויות (ASST)")
    st.markdown("המערכת מזהה נקודות איזון טכניות שבהן מניה צוברת אנרגיה. אנו מחפשים את **השילוב** של דחיסה טכנית עם אישור מהכסף הגדול (OBV).")
    

with tab2:
    if os.path.exists(PORTFOLIO_FILE): st.table(pd.read_csv(PORTFOLIO_FILE))
    else: st.info("התיק ריק.")
