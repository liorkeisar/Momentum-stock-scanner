import streamlit as st
import yfinance as yf
import pandas as pd
import time

# הגדרות עמוד
st.set_page_config(page_title="סורק מניות מוסדי - Wyckoff", layout="wide")
st.title("◈ סורק מניות מוסדי - Wyckoff Accumulation")

# --- פונקציות עזר ---
@st.cache_data
def load_data():
    """טעינת ה-CSV וסינון מותאם למבנה הקובץ שלך"""
    df = pd.read_csv("nasdaq_screener.csv")
    
    # ניקוי עמודת המחיר: הסרת סימני $ ו-, והמרה למספר
    df['Price'] = df['Last Sale'].replace('[\$,]', '', regex=True).astype(float)
    
    # סינון: רק מניות עם מחיר מעל 5$
    return df[df['Price'] > 5]

def calculate_wyckoff_score(df):
    """חישוב ציון וייקוף מבוסס נפח ותנודתיות"""
    if len(df) < 20: return 0, 0, 0
    recent = df.tail(20)
    
    down = recent[recent['Close'] < recent['Close'].shift(1)]
    up = recent[recent['Close'] >= recent['Close'].shift(1)]
    
    avg_vol_down = down['Volume'].mean() if len(down) > 0 else 1
    avg_vol_up = up['Volume'].mean() if len(up) > 0 else 1
    vol_ratio = avg_vol_up / avg_vol_down if avg_vol_down != 0 else 1
    
    hi, lo = recent['High'].max(), recent['Low'].min()
    rw = (hi - lo) / ((hi + lo) / 2) * 100
    
    score = 0
    if vol_ratio > 1.2: score += 40
    if rw < 7: score += 40
    if rw < 4: score += 20
    return min(score, 100), vol_ratio, rw

# --- ממשק משתמש ---
if 'results_df' not in st.session_state: st.session_state['results_df'] = None
if 'watchlist' not in st.session_state: st.session_state['watchlist'] = []

# טעינת הנתונים
try:
    all_tickers = load_data()['Symbol'].tolist()
except Exception as e:
    st.error(f"שגיאה בטעינת הקובץ: {e}. וודא ש-nasdaq_screener.csv בתיקייה הראשית.")
    st.stop()

# פאנל צדי להגדרות
num_to_scan = st.sidebar.slider("כמות מניות לסריקה:", 10, 500, 50)
if st.sidebar.button("הרץ סריקה"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.sidebar.empty()
    
    for i, ticker in enumerate(all_tickers[:num_to_scan]):
        try:
            status_text.text(f"סורק את: {ticker}")
            time.sleep(0.1) # מניעת חסימת IP
            df = yf.Ticker(ticker).history(period="3mo")
            score, vr, rw = calculate_wyckoff_score(df)
            results.append({"Ticker": ticker, "Wyckoff_Score": score, "Vol_Ratio": vr, "Range_Width": rw})
            progress_bar.progress((i + 1) / num_to_scan)
        except: continue
    
    st.session_state['results_df'] = pd.DataFrame(results)
    status_text.text("הסריקה הושלמה!")

# --- תצוגה וניהול ---
if st.session_state['results_df'] is not None:
    st.subheader("תוצאות הסריקה")
    df = st.session_state['results_df'].sort_values("Wyckoff_Score", ascending=False)
    st.dataframe(df, use_container_width=True)
    
    # בחירת מועדפים
    watchlist = st.multiselect("בחר מניות להוספה למועדפים:", df['Ticker'].tolist(), default=st.session_state['watchlist'])
    st.session_state['watchlist'] = watchlist
    
    if watchlist:
        st.subheader("רשימת מועדפים")
        watchlist_df = df[df['Ticker'].isin(watchlist)]
        st.dataframe(watchlist_df)
        
        st.download_button(
            "📥 הורד את המועדפים ל-Google Sheets", 
            data=watchlist_df.to_csv(index=False), 
            file_name='my_watchlist.csv',
            mime='text/csv'
        )
