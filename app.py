def calculate_wyckoff_metrics(df):
    if len(df) < 30: return None
    
    # 1. VR - הקיים
    recent = df.tail(20)
    up_vol = recent[df['Close'] >= df['Close'].shift(1)]['Volume'].mean()
    down_vol = recent[df['Close'] < df['Close'].shift(1)]['Volume'].mean()
    vr = up_vol / down_vol
    
    # 2. הוספת מדד Efficiency (המאמץ מול התוצאה)
    # מחשב את השינוי היומי הממוצע ביחס לווליום הממוצע
    daily_change = (df['High'] - df['Low']).mean()
    avg_vol = df['Volume'].mean()
    efficiency = daily_change / (avg_vol / 1000000) # כמה "תנועה" קיבלנו לכל מיליון מניות
    
    # 3. ציון משוקלל
    score = (40 if vr > 1.2 else 0) + (30 if efficiency < 1.0 else 0) + 30
    return round(score, 2), round(vr, 2), round(efficiency, 2)
import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף")

PORTFOLIO_FILE = 'portfolio.csv'

# --- פונקציות עזר ---
def get_available_lists(): return [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]

@st.cache_data
def load_selected_list(filename):
    # תיקון: קריאה ללא כותרות כדי למנוע אובדן שורות, לקיחת העמודה הראשונה
    df = pd.read_csv(filename, header=None)
    return df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist()

def calculate_wyckoff_score(df):
    # הגנה מפני נתונים חסרים
    if df is None or len(df) < 30: return 0, 0, 0
    recent = df.tail(20)
    
    # חישוב ווליום עם הגנה מחלוקה באפס
    up = recent[recent['Close'] >= recent['Close'].shift(1)]['Volume'].mean()
    down = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].mean()
    
    vr = (up / down) if (pd.notna(down) and down > 0) else 1
    rw = (recent['High'].max() - recent['Low'].min()) / ((recent['High'].max() + recent['Low'].min()) / 2) * 100
    
    score = min((40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0), 100)
    return score, round(vr, 2), round(rw, 2)

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice']).to_csv(PORTFOLIO_FILE, index=False)
    return pd.read_csv(PORTFOLIO_FILE)

# --- ממשק טאבים ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

def show_buttons(ticker):
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.link_button("Yahoo", f"https://finance.yahoo.com/quote/{ticker}")
    with c2: st.link_button("Finviz", f"https://finviz.com/quote.ashx?t={ticker}")
    with c3: st.link_button("Investing", f"https://www.investing.com/search/?q={ticker}")
    with c4: st.link_button("Webull", f"https://www.webull.com/quote/{ticker}")

with tab1:
    available_lists = get_available_lists()
    selected_file = st.sidebar.selectbox("בחר רשימה:", available_lists)
    min_score = st.sidebar.slider("ציון מינימלי:", 0, 100, 40)

    if st.sidebar.button("הרץ סריקה"):
        tickers = load_selected_list(selected_file)
        results = []
        bar = st.progress(0)
        for i, ticker in enumerate(tickers):
            bar.progress((i + 1) / len(tickers))
            try:
                df = yf.Ticker(ticker).history(period="6mo") # טווח ארוך יותר ליציבות
                if not df.empty and df['Volume'].iloc[-1] > 100000:
                    score, vr, rw = calculate_wyckoff_score(df)
                    results.append({"Ticker": ticker, "Score": score, "Price": round(df['Close'].iloc[-1], 2), "VR": vr})
            except: continue
        st.session_state['results_df'] = pd.DataFrame(results)
        st.rerun()

    if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
        df = st.session_state['results_df']
        df = df[df['Score'] >= min_score]
        st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)
        
        to_add = st.selectbox("בחר מניה לעבודה:", df['Ticker'].tolist())
        if st.button("הוסף לתיק ההשקעות 💼"):
            price = df[df['Ticker'] == to_add]['Price'].values[0]
            new_entry = pd.DataFrame({'Ticker': [to_add], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
            new_entry.to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
            st.success(f"{to_add} נוספה!")
        show_buttons(to_add)

with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        # עדכון מחירים בזמן אמת
        for i, row in portfolio.iterrows():
            try:
                curr = yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1]
                portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
                portfolio.loc[i, 'Performance'] = f"{round(((curr - row['EntryPrice']) / row['EntryPrice']) * 100, 2)}%"
            except: continue
        
        st.dataframe(portfolio, use_container_width=True)
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())
        show_buttons(to_manage)
        
        if st.button("מחק מניה מהתיק 🗑️"):
            portfolio = portfolio[portfolio['Ticker'] != to_manage]
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()
    else: st.info("התיק ריק.")
