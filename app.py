import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# הגדרת דף
st.set_page_config(layout="wide", page_title="Professional Momentum Radar")
st.title("🏹 Pro Momentum Scanner (200+ Stocks)")

target_stocks = [
    "NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", "QCOM", "TXN", "ADI", "MRVL", "KLAC",
    "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS",
    "MSFT", "GOOGL", "META", "AMZN", "AAPL", "PLTR", "SOUN", "BBAI", "AI", "INTC", "ANET",
    "COIN", "MARA", "RIOT", "CLSK", "MSTR", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", "UPST", "COF", "NU", "MELI", "SE",
    "FSLR", "ENPH", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "NEE", "GEV", "RUN", "BLNK", "CHPT", "QS", "BE", "CAT", "DE",
    "LLY", "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "EXAS", "NVAX", "EDIT", "BEAM", "NTLA",
    "SHOP", "CHWY", "TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "WMT", "TGT", "COST", "DIS", "NFLX", "UBER", "LYFT",
    "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL", "DRI",
    "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "GE", "BA", "CIFR", "WEX", "PAYC", "PCTY"
]

if st.button("🚀 קיסר מומנטום "):
    with st.spinner("סורק נתונים מכל הסקטורים..."):
        # הורדת נתונים מרוכזת
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        signals = []

        for ticker in target_stocks:
            try:
                # ניקוי מבנה נתונים
                data = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
                if len(data) < 60: continue

                # חישובים טכניים
                data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
                delta = data['Close'].diff()
                data['RSI'] = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean() / (-delta.where(delta < 0, 0).rolling(14).mean() + 1e-9))))
                tr = pd.concat([data['High']-data['Low'], abs(data['High']-data['Close'].shift()), abs(data['Low']-data['Close'].shift())], axis=1).max(axis=1)
                data['ATR'] = tr.rolling(14).mean()

                curr = data.iloc[-1]
                highest_20 = data['High'].iloc[-21:-1].max()
                avg_vol = data['Volume'].iloc[-21:-1].mean()

                # לוגיקת איתות פריצה
                if curr['Close'] > highest_20 and curr['Volume'] > (avg_vol * 1.2) and curr['Close'] > curr['EMA50'] and 50 < curr['RSI'] < 70:
                    score = 1
                    if curr['Volume'] > (avg_vol * 2.0): score += 1
                    if 55 <= curr['RSI'] <= 65: score += 1
                    
                    signals.append({
                        "Ticker": ticker, 
                        "Score": score, 
                        "Price": round(curr['Close'], 2),
                        "TP": round(curr['Close'] + (4 * data['ATR'].iloc[-1]), 2),
                        "SL": round(curr['Close'] - (2 * data['ATR'].iloc[-1]), 2)
                    })
            except: continue

        if signals:
            # הצגת תוצאות ממוינות
            df_final = pd.DataFrame(signals).sort_values(by="Score", ascending=False)
            st.dataframe(df_final, use_container_width=True, hide_index=True)
        else:
            st.info("לא נמצאו איתותים חזקים כרגע.")
