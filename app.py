import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# הגדרות
st.set_page_config(page_title="KEISAR Bottom Hunter", layout="wide")
SCAN_RESULTS_FILE = 'scan_results.csv'
PORTFOLIO_FILE = 'portfolio.csv'

def get_indicators(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if info.get('marketCap', 0) < 300_000_000: return None
        if info.get('averageVolume', 0) < 200_000: return None
        
        df = stock.history(period="1y")
        if df is None or len(df) < 252: return None
        
        yearly_low = df['Close'].min()
        current_price = df['Close'].iloc[-1]
        if current_price > (yearly_low * 1.15): return None

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Squeeze'] = ((df['MA20'] + (df['STD'] * 2)) - (df['MA20'] - (df['STD'] * 2))) / df['Close']
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
        df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
        return df.dropna()
    except: return None

def calculate_score(df):
    score = 0
    if df['Squeeze'].iloc[-1] < 0.10: score += 2
    if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 1
    if df['RVOL'].iloc[-1] > 1.5: score += 1
    return score

# --- ממשק ---
st.title("◈ KEISAR: סורק שפל (Bottom Hunter)")
tab1, tab2 = st.tabs(["📊 סורק", "💼 תיק"])

with tab1:
    all_files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan' not in f])
    selected_files = st.sidebar.multiselect("בחר רשימות:", all_files)

    if st.button("🚀 הפעל סריקה"):
        if not selected_files:
            st.warning("אנא בחר לפחות רשימה אחת מהתפריט בצד!")
        else:
            # מחיקת תוצאות קודמות כדי לוודא שסורקים מחדש
            if os.path.exists(SCAN_RESULTS_FILE): os.remove(SCAN_RESULTS_FILE)
            
            master_list = []
            with st.spinner('סורק את כל הרשימות שנבחרו...'):
                for file in selected_files:
                    # קריאת הקובץ הנבחר
                    tickers = pd.read_csv(file, header=None).iloc[:, 0].dropna().unique()
                    for ticker in tickers:
                        df = get_indicators(ticker)
                        if df is not None:
                            master_list.append({
                                "Ticker": ticker, 
                                "Score": calculate_score(df), 
                                "Price": round(float(df['Close'].iloc[-1]), 2), 
                                "RVOL": round(float(df['RVOL'].iloc[-1]), 2)
                            })
            
            if master_list:
                df_final = pd.DataFrame(master_list).sort_values(by="Score", ascending=False)
                df_final.to_csv(SCAN_RESULTS_FILE, index=False)
                st.success(f"הסריקה הסתיימה! נמצאו {len(df_final)} מניות.")
                st.rerun()
            else:
                st.error("לא נמצאו מניות שעומדות בתנאים ברשימות שנבחרו.")

    if os.path.exists(SCAN_RESULTS_FILE):
        df_res = pd.read_csv(SCAN_RESULTS_FILE)
        df_res['Signal'] = df_res.apply(lambda row: '✅ HIGH MOMENTUM' if row['Score'] >= 3 and row['RVOL'] > 1.5 else '', axis=1)
        st.dataframe(df_res, use_container_width=True)
        # ... (שאר קוד הניתוח נשאר זהה)
