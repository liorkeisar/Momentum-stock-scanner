import streamlit as st
import yfinance as yf
import pandas as pd
import os

# --- הגדרות ---
st.set_page_config(page_title="TITAN Wyckoff Pro", layout="wide")
st.title("◈ TITAN: מערכת וייקוף מוסדית")

# --- פונקציות תשתית ---
def load_tickers(filename):
    # קריאת הקובץ והסרת כותרות במידה וקיימות
    try:
        df = pd.read_csv(filename, header=None)
        # לוקחים את העמודה הראשונה ומוודאים שהיא טקסט
        return df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist()
    except Exception:
        return []

def calculate_wyckoff(df):
    if len(df) < 30: return None
    
    # חישוב וייקוף בסיסי
    recent = df.tail(20)
    up_vol = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down_vol = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    
    if pd.isna(up_vol) or pd.isna(down_vol) or down_vol == 0: return None
    
    vr = up_vol / down_vol
    rw = (recent['High'].max() - recent['Low'].min()) / recent['Close'].iloc[-1] * 100
    score = (40 if vr > 1.5 else 0) + (40 if rw < 5 else 0)
    
    return round(score, 2), round(vr, 2), round(rw, 2)

# --- ממשק משתמש ---
files = [f for f in os.listdir('.') if f.endswith('.csv')]
selected_file = st.sidebar.selectbox("בחר רשימת מניות:", files)

if st.sidebar.button("הרץ סריקה"):
    tickers = load_tickers(selected_file)
    results = []
    bar = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        bar.progress((i + 1) / len(tickers))
        try:
            # משיכת נתונים מ-Yahoo Finance
            df = yf.Ticker(ticker).history(period="6mo", interval="1d")
            
            if not df.empty and df['Volume'].iloc[-1] > 100000:
                res = calculate_wyckoff(df)
                if res:
                    score, vr, rw = res
                    results.append({
                        "Ticker": ticker,
                        "Score": score,
                        "Price": round(float(df['Close'].iloc[-1]), 2),
                        "VR": vr,
                        "RW%": rw
                    })
        except: continue
    
    if results:
        st.session_state['results'] = pd.DataFrame(results)
    else:
        st.error("לא נמצאו נתונים תואמים. בדוק את פורמט הטיקרים בקובץ.")

# הצגת טבלה
if 'results' in st.session_state and not st.session_state['results'].empty:
    st.dataframe(st.session_state['results'].sort_values("Score", ascending=False), use_container_width=True)
