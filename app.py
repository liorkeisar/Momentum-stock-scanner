import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Large-Cap Accumulation Scanner")

# חלוקה לסקטורים ומדדים מובילים
major_indices = {
    "Big Tech (FAANG+)": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "NFLX"],
    "Financial & Banks": ["JPM", "BAC", "GS", "MS", "WFC", "C", "AXP"],
    "Major ETFs": ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "SMH"]
}

tab_names = list(major_indices.keys())
tabs = st.tabs(tab_names)

def scan_major_market(tickers):
    results = []
    for ticker in tickers:
        try:
            # שימוש בטווח נתונים גדול למניות יציבות
            df = yf.Ticker(ticker).history(period="150d")
            if len(df) < 90: continue
            
            # MFI (30 יום לאיסוף)
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            mf = tp * df['Volume']
            pos = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
            neg = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
            mfi = 100 - (100 / (1 + (pos / neg)))
            
            # ווליום ממוצע (30 יום)
            avg_vol_short = df['Volume'].rolling(5).mean().iloc[-1]
            avg_vol_long = df['Volume'].rolling(30).mean().iloc[-1]
            
            # לוגיקת איסוף למניות גדולות: MFI עולה ב-30 יום האחרונים + מחיר יציב/מתקן
            # במניות גדולות אנחנו מחפשים התכנסות ולא רק ירידה חדה
            if mfi.iloc[-1] > mfi.iloc[-30] and avg_vol_short > avg_vol_long * 1.05:
                results.append({
                    "Ticker": ticker,
                    "Price": round(df['Close'].iloc[-1], 2),
                    "MFI_30d": round(mfi.iloc[-1], 1),
                    "Trend": "צבירה חיובית 🟢"
                })
        except: continue
    return pd.DataFrame(results)

# לולאה בטוחה על הלשוניות
for i, tab_name in enumerate(tab_names):
    with tabs[i]:
        tickers = major_indices[tab_name]
        if st.button(f"סרוק מניות ב-{tab_name}", key=f"btn_{i}"):
            with st.spinner(f"סורק מדדים מובילים..."):
                df = scan_major_market(tickers)
                if not df.empty:
                    st.dataframe(df.sort_values(by="MFI_30d", ascending=False), use_container_width=True)
                else:
                    st.info(f"לא נמצאו סימני איסוף מובהקים כרגע במדד {tab_name}.")

st.sidebar.markdown("### דגש למדדים מובילים:")
st.sidebar.write("בניגוד לפני-סטוקס, כאן אנחנו מחפשים **התכנסות עם ווליום**. כש-MFI עולה במדדים כמו SPY או QQQ, זה מעיד על כניסת מוסדיים.")
