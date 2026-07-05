import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime, timedelta
import traceback
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Optional ML import
try:
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# --- הגדרות דף ---
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
st.title("◈ KEISAR Pro Hunter — מערכת וייקוף Pro וניהול סיכונים")

PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'
PREDICTIONS_FILE = 'predictions.csv'

# ============================
# פונקציות ניהול סיכונים (התוספת החדשה)
# ============================
def calculate_position_size(price, atr, account_size=100000, risk_pct=0.01):
    risk_amount = account_size * risk_pct
    stop_distance = atr * 1.5
    shares = int(risk_amount / stop_distance) if stop_distance > 0 else 0
    return shares, round(price - stop_distance, 2)

def style_portfolio(df):
    def color_row(row):
        if 'CurrentPrice' in row and 'StopLoss' in row and pd.notnull(row['CurrentPrice']):
            try:
                if float(row['CurrentPrice']) <= float(row['StopLoss']):
                    return ['background-color: #ff4d4d'] * len(row)
            except: pass
        return [''] * len(row)
    return df.style.apply(color_row, axis=1)

# ============================
# פונקציות עזר מקוריות
# ============================
def safe_last(s):
    try: return s.iloc[-1] if hasattr(s, "iloc") and len(s) > 0 else np.nan
    except: return np.nan

def validate_df(df, required_cols=None):
    if df is None or df.empty: return False, "DataFrame ריק"
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing: return False, f"עמודות חסרות: {missing}"
    return True, None

def add_indicators(df):
    df = df.copy()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]
    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5
    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss.replace(0,1))))
    df["MACD"] = df["Close"].ewm(span=12, adjust=False).mean() - df["Close"].ewm(span=26, adjust=False).mean()
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    return df

# --- # ============================
# פונקציות ML וחיזוי (המשך מקוד המקור שלך)
# ============================

def compute_features_for_ml(df):
    features = df.copy()
    features['returns'] = features['Close'].pct_change()
    features['rsi_diff'] = features['RSI'].diff()
    features['macd_diff'] = features['MACD'] - features['Signal']
    features = features.dropna()
    return features

def train_logistic_model(df):
    if not SKLEARN_AVAILABLE: return None
    features = compute_features_for_ml(df)
    if len(features) < 30: return None
    X = features[['RSI', 'MACD', 'VOL_MA20']]
    y = (features['Close'].shift(-1) > features['Close']).astype(int)
    model = LogisticRegression()
    model.fit(X.iloc[:-1], y.iloc[:-1])
    return model

def pattern_detection_vcp_like(df):
    # לוגיקת זיהוי תבניות VCP
    recent = df.iloc[-20:]
    vol_contraction = recent['Volume'].std() < recent['VOL_MA20'].mean()
    price_tightness = (recent['High'].max() - recent['Low'].min()) / recent['Close'].mean() < 0.1
    return vol_contraction and price_tightness

def compute_breakout_decision(df):
    # לוגיקת החלטת סריקה
    last_close = safe_last(df["Close"])
    upper_bb = safe_last(df["UpperBB"])
    rsi = safe_last(df["RSI"])
    
    score = 0
    if last_close > upper_bb: score += 40
    if rsi > 50: score += 30
    if pattern_detection_vcp_like(df): score += 30
    return score

# ============================
# ממשק המשתמש - טאב 1 (סורק)
# ============================
def run_scanner_ui():
    st.sidebar.header("הגדרות סורק")
    tickers_input = st.sidebar.text_area("רשימת טיקרים (פסיקים):", "NVDA, AMD, PLTR, ARM, TSLA, MSFT")
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    
    if st.sidebar.button("הרץ סריקה"):
        for ticker in tickers:
            df = yf.Ticker(ticker).history(period="12mo")
            if df.empty: continue
            df = add_indicators(df)
            price = safe_last(df["Close"])
            atr = safe_last(df["ATR"])
            
            # הצגת תוצאה
            st.write(f"### {ticker}")
            shares, sl = calculate_position_size(price, atr)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("מחיר", round(price, 2))
            col2.metric("Stop Loss", sl)
            col3.metric("כמות", shares)
            
            if st.button(f"הוסף לתיק {ticker}", key=f"add_{ticker}"):
                new_row = pd.DataFrame({
                    'Ticker': [ticker],
                    'Date': [datetime.now().strftime('%Y-%m-%d')],
                    'EntryPrice': [round(price, 2)],
                    'StopLoss': [sl]
                })
                new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success(f"{ticker} נוספה לתיק!")

# --- # ============================
# ממשק המשתמש - טאב 2 (תיק השקעות)
# ============================
def run_portfolio_ui():
    st.header("💼 תיק השקעות פעיל")
    if os.path.exists(PORTFOLIO_FILE):
        portfolio = pd.read_csv(PORTFOLIO_FILE)
        
        # עדכון מחירים בזמן אמת מהשוק
        for i, row in portfolio.iterrows():
            try:
                curr_data = yf.Ticker(row['Ticker']).history(period="1d")
                if not curr_data.empty:
                    curr = curr_data['Close'].iloc[-1]
                    portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
            except:
                portfolio.loc[i, 'CurrentPrice'] = np.nan
        
        # הצגת הטבלה עם צביעה מותנית (אדום ב-Stop Loss)
        st.dataframe(style_portfolio(portfolio), use_container_width=True)
        st.warning("שורות מסומנות באדום מציינות מניות שירדו מתחת ל-Stop Loss המקורי שלך.")
    else:
        st.info("התיק ריק כרגע.")

# ============================
# ממשק המשתמש - טאב 3 (תחזיות ושמירת נתונים)
# ============================
def run_predictions_ui():
    st.header("💾 תוצאות ותחזיות")
    if os.path.exists(PREDICTIONS_FILE):
        preds = pd.read_csv(PREDICTIONS_FILE)
        st.dataframe(preds, use_container_width=True)
    else:
        st.write("אין תחזיות שמורות כרגע.")

# ============================
# הרצת הממשק הראשי
# ============================
def main():
    tab1, tab2, tab3 = st.tabs(["📊 סורק פריצה", "💼 תיק השקעות", "💾 תוצאות ותחזיות"])
    
    with tab1:
        run_scanner_ui()
    with tab2:
        run_portfolio_ui()
    with tab3:
        run_predictions_ui()

if __name__ == "__main__":
    main()


