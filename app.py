import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🚀 AI & Semi Breakout Scanner (Massive Scan)")

# רשימה מורחבת של מניות AI וסמיקונדקטורס
ai_tickers = [
    "NVDA", "AMD", "SOUN", "PLTR", "ARM", "MRVL", "AVGO", "INTC", "TSM", "ON", "QCOM",
    "MU", "ADI", "TXN", "NXPI", "MCHP", "TER", "KLAC", "LRCX", "AMAT", "SSYS", "DDD",
    "C3AI", "AI", "SNPS", "CDNS", "MSFT", "GOOGL", "META", "AMZN", "SNOW", "DDOG"
]

def scan_breakout(tickers):
    results = []
    # סריקה בחבילות של 10 כדי למנוע עומס
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="60d")
            if len(df) < 30: continue
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # MACD
            ema12 = df['Close'].ewm(span=12).mean()
            ema26 = df['Close'].ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()
            
            # תנאי פריצה
            is_near_high = df['Close'].iloc[-1] >= (df['High'].rolling(20).max() * 0.98)
            vol_spike = df['Volume'].iloc[-1] > (df['Volume'].rolling(20).mean().iloc[-1] * 1.5)
            is_bullish_macd = macd.iloc[-1] > signal.iloc[-1]
            
            if is_near_high and vol_spike and is_bullish_macd and 60 < rsi.iloc[-1] < 75:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "RSI": round(rsi.iloc[-1], 1)
                })
        except: continue
    return pd.DataFrame(results)

if st.button("סרוק את כל מניות ה-AI והסמיקונדקטורס"):
    with st.spinner("סורק מקסימום מניות... אנא המתן"):
        df = scan_breakout(ai_tickers)
        if not df.empty:
            st.dataframe(df.sort_values(by="RSI", ascending=False), use_container_width=True)
        else:
            st.info("לא נמצאו מניות בפריצה כרגע. נסה שוב מחר.")

st.sidebar.write(f"מותקן כרגע: {len(ai_tickers)} מניות במעקב.")
