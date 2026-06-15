import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף")

PORTFOLIO_FILE = 'portfolio.csv'

# --- מילון אתרים ---
ANALYSIS_SITES = {
    "Yahoo Finance": "https://finance.yahoo.com/quote/",
    "Finviz": "https://finviz.com/quote.ashx?t=",
    "Investing.com": "https://www.investing.com/search/?q=",
    "Webull": "https://www.webull.com/quote/"
}

# --- פונקציות עזר ---
def get_available_lists(): return [f for f in os.listdir('.') if f.endswith('.csv')]

@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    cols = ['Symbol', 'Ticker', 'Symbol ', 'TICKER', 'Symbol (NASDAQ)']
    target = next((c for c in cols if c in df.columns), df.columns[0])
    return df[target].dropna().astype(str).tolist()

def calculate_wyckoff_score(df):
    if df is None or len(df) < 20: return 0, 0, 0
    recent = df.tail(20)
    up = recent[recent['Close'] >= recent['Close'].shift(1)]
    down = recent[recent['Close'] < recent['Close'].shift(1)]
    vr = (up['Volume'].mean() / down['Volume'].mean()) if down['Volume'].mean() > 0 else 1
    rw = (recent['High'].max() - recent['Low'].min()) / ((recent['High'].max() + recent['Low'].min()) / 2) * 100
    return min((40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0), 100), vr, rw

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df
    try:
        return pd.read_csv(PORTFOLIO_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df

# --- פונקציית הצגת כפתור בחירה ---
def display_analysis_selector(ticker):
    col1, col2 = st.columns([1, 2])
    with col1:
        site_name = st.selectbox("בחר פלטפורמת ניתוח:", list(ANALYSIS_SITES.keys()), key=f"site_{ticker}")
    with col2:
        st.write("") # מרווח לעיצוב
        st.write("") 
        st.link_button(f"עבור ל-{site_name}", f"{ANALYSIS_SITES[site_name]}{ticker}")

# --- ממשק טאבים ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    available_lists = get_available_lists()
    selected_file = st.sidebar.selectbox("בחר רשימה:", available_lists)
    min_score = st.sidebar.slider("ציון מינימלי:", 0, 100, 40)

    if st.sidebar.button("הרץ סריקה"):
        tickers = load_selected_list(selected_file)
        results = []
        for ticker in tickers[:30]:
            try:
                df = yf.Ticker(ticker).history(period="3mo")
                if not df.empty:
                    score, vr, rw = calculate_wyckoff_score(df)
                    results.append({"Ticker": ticker, "Score": score, "Price": round(df['Close'].iloc[-1], 2)})
            except: continue
        st.session_state['results_df'] = pd.DataFrame(results)
        st.rerun()

    if st.session_state.get('results_df') is not None:
        df = st.session_state['results_df']
        df = df[df['Score'] >= min_score]
        st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)
        
        st.divider()
        to_add = st.selectbox("בחר מניה לעבודה:", df['Ticker'].tolist())
        if st.button("הוסף לתיק ההשקעות 💼"):
            price = df[df['Ticker'] == to_add]['Price'].values[0]
            new_row = pd.DataFrame({'Ticker': [to_add], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
            new_row.to_csv(PORTFOLIO_FILE, mode='a', header=False, index=False)
            st.success(f"{to_add} נוספה!")
        
        display_analysis_selector(to_add)

with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        for i, row in portfolio.iterrows():
            try:
                curr = yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1]
                portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
                portfolio.loc[i, 'Performance'] = f"{round(((curr - row['EntryPrice']) / row['EntryPrice']) * 100, 2)}%"
            except: continue
        
        st.dataframe(portfolio, use_container_width=True)
        st.divider()
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())
        
        display_analysis_selector(to_manage)
        
        if st.button("מחק מניה מהתיק 🗑️"):
            portfolio = portfolio[portfolio['Ticker'] != to_manage]
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()
    else: st.info("התיק ריק.")
