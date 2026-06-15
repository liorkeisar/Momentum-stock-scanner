import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# הגדרת דף ה-Dashboard
st.set_page_config(page_title="סורק מניות מוסדי", layout="wide")

st.title("◈ סורק מניות מוסדי - Wyckoff Accumulation")
st.markdown("סורק המבוסס על ניתוח נפח ותנודתיות לזיהוי שלבי איסוף (Accumulation).")

# --- לוגיקת Wyckoff ---
def calculate_wyckoff_score(df):
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

# --- פונקציית סריקה ---
def analyze_stock(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo")
        score, vr, rw = calculate_wyckoff_score(df)
        return {"Ticker": ticker, "Wyckoff_Score": score, "Vol_Ratio": round(vr, 2), "Range_Width": round(rw, 2)}
    except: return None

# --- ממשק משתמש ---
TICKERS = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "NFLX", "INTC"]

if st.sidebar.button("הרץ סריקת איסוף מוסדי"):
    data = [analyze_stock(t) for t in TICKERS]
    df_results = pd.DataFrame([d for d in data if d])
    
    st.dataframe(
        df_results.sort_values("Wyckoff_Score", ascending=False),
        column_config={"Wyckoff_Score": st.column_config.ProgressColumn("ציון איסוף", min_value=0, max_value=100)},
        use_container_width=True
    )

    selected = st.selectbox("בחר מניה לניתוח עומק:", TICKERS)
    df = yf.Ticker(selected).history(period="6mo")
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    st.plotly_chart(fig, use_container_width=True)
