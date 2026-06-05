import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TradeEdge Pro")

# --- עיצוב CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&display=swap');
    .stApp { background-color: #0d1117 !important; color: #e6edf3 !important; font-family: 'Syne', sans-serif; }
    .trade-card { background: #161b22; border: 1px solid #21262d; border-radius: 16px; padding: 16px; margin-bottom: 12px; }
    .ticker-title { font-weight: 800; font-size: 18px; color: #e6edf3; }
    .price-text { font-weight: 800; font-size: 18px; color: #22d3a0; }
    .filter-box { background: #161b22; padding: 10px; border-radius: 12px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- לוגיקת סורק ---
TICKERS = ["NVDA", "AXON", "CRWD", "META", "SMCI", "LULU"]

def run_scanner(ticker, mode):
    try:
        df = yf.Ticker(ticker).history(period="30d")
        if len(df) < 20: return None
        # הלוגיקה שלך לסורקים
        if mode == "REVERSAL":
            is_valid = df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1]
        else:
            is_valid = df['Close'].iloc[-1] > df['High'].iloc[-20:].max()
        return {"ticker": ticker, "price": df['Close'].iloc[-1]} if is_valid else None
    except: return None

# --- ממשק ---
st.markdown('<h1 style="font-family: \'Syne\'; font-weight: 800;">TradeEdge Dashboard</h1>', unsafe_allow_html=True)

# אזור המסננים
with st.container():
    mode = st.radio("בחר אסטרטגיה לסריקה:", ["REVERSAL", "BREAKOUT"], horizontal=True)
    if st.button("הפעל סורק"):
        with st.spinner("סורק נתונים..."):
            with ThreadPoolExecutor() as ex:
                results = [r for r in ex.map(lambda t: run_scanner(t, mode), TICKERS) if r is not None]
            
            # הצגת תוצאות בעיצוב החדש
            for s in results:
                st.markdown(f"""
                    <div class="trade-card">
                        <div style="display:flex; justify-content:space-between;">
                            <div class="ticker-title">{s['ticker']}</div>
                            <div class="price-text">${s['price']:.2f}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
