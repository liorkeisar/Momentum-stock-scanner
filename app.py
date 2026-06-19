import streamlit as st
import yfinance as yf
import pandas as pd
import os

# --- הגדרות ותשתית ---
st.set_page_config(page_title="TITAN Wyckoff Pro", layout="wide")
st.title("◈ TITAN: מערכת ניהול השקעות וייקוף")
PORTFOLIO_FILE = 'portfolio.csv'

def init_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=['Ticker', 'Price', 'StopLoss', 'Target']).to_csv(PORTFOLIO_FILE, index=False)

def load_tickers(filename):
    df = pd.read_csv(filename, header=None)
    return df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist()

# --- מנוע חישוב ---
def calculate_wyckoff(df):
    if df is None or len(df) < 30: return None
    recent = df.tail(20)
    up_vol = recent[df['Close'] >= df['Close'].shift(1)]['Volume'].mean()
    down_vol = recent[df['Close'] < df['Close'].shift(1)]['Volume'].mean()
    if pd.isna(up_vol) or pd.isna(down_vol) or down_vol == 0: return None
    
    vr = up_vol / down_vol
    rw = (df['High'].max() - df['Low'].min()) / df['Close'].iloc[-1] * 100
    atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
    
    score = (40 if vr > 1.5 else 0) + (40 if rw < 5 else 0)
    return round(score, 2), round(vr, 2), round(rw, 2), round(float(df['Close'].iloc[-1]), 2), round(float(atr), 2)

# --- ממשק ---
tab1, tab2 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות"])

with tab1:
    files = [f for f in os.listdir('.') if f.endswith('.csv') and f != PORTFOLIO_FILE]
    selected_file = st.sidebar.selectbox("בחר רשימת מניות:", files)
    
    if st.sidebar.button("הרץ סריקה"):
        results = []
        for ticker in load_tickers(selected_file):
            try:
                data = yf.Ticker(ticker).history(period="6mo", interval="1d")
                if not data.empty:
                    res = calculate_wyckoff(data)
                    if res:
                        score, vr, rw, price, atr = res
                        results.append({"Ticker": ticker, "Score": score, "Price": price, "Stop": round(price - (2*atr), 2), "Target": round(price + (6*atr), 2), "VR": vr})
            except: continue
        st.session_state['results'] = pd.DataFrame(results)
        st.rerun()

    if 'results' in st.session_state:
        df_res = st.session_state['results']
        st.dataframe(df_res, use_container_width=True)
        
        # הוספה לתיק
        to_add = st.selectbox("בחר מניה להוספה לתיק:", df_res['Ticker'].tolist())
        if st.button("הוסף לתיק השקעות ➕"):
            row = df_res[df_res['Ticker'] == to_add].iloc[0]
            portfolio = pd.read_csv(PORTFOLIO_FILE)
            portfolio = pd.concat([portfolio, pd.DataFrame([row])], ignore_index=True)
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{to_add} נוספה בהצלחה!")

with tab2:
    init_portfolio()
    st.subheader("מניות בתיק השקעות")
    portfolio = pd.read_csv(PORTFOLIO_FILE)
    st.dataframe(portfolio, use_container_width=True)
    
    if st.button("נקה תיק השקעות 🗑️"):
        os.remove(PORTFOLIO_FILE)
        st.rerun()
