import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# הגדרת דף
st.set_page_config(layout="wide", page_title="Scored ATR Radar")
st.title("🏹 Scored ATR Trading Radar")

target_stocks = [
    "NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT",
    "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC",
    "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM",
    "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN",
    "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI",
    "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN"
]

if st.button("🚀 הרץ סריקת מומנטום"):
    with st.spinner("סורק מניות ומדרג איכות..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        signals = []

        for ticker in target_stocks:
            try:
                data = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
                if len(data) < 60: continue

                # חישוב אינדיקטורים (לפי הלוגיקה שלך)
                data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
                delta = data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / (loss + 1e-9)
                data['RSI'] = 100 - (100 / (1 + rs))
                
                tr = pd.concat([data['High']-data['Low'], abs(data['High']-data['Close'].shift()), abs(data['Low']-data['Close'].shift())], axis=1).max(axis=1)
                data['ATR'] = tr.rolling(14).mean()

                curr = data.iloc[-1]
                highest_20 = data['High'].iloc[-21:-1].max()
                lowest_20 = data['Low'].iloc[-21:-1].min()
                avg_vol = data['Volume'].iloc[-21:-1].mean()

                # בדיקת איתותים
                score = 0
                direction = ""
                
                if curr['Close'] > highest_20 and curr['Volume'] > (avg_vol * 1.2) and curr['Close'] > curr['EMA50'] and 50 < curr['RSI'] < 70:
                    direction = "BUY 🟢"
                    if curr['Volume'] > (avg_vol * 2.0): score += 1
                    if 55 <= curr['RSI'] <= 65: score += 1
                    if (curr['Close'] - curr['EMA50']) / curr['EMA50'] < 0.05: score += 1
                
                elif curr['Close'] < lowest_20 and curr['Volume'] > (avg_vol * 1.2) and curr['Close'] < curr['EMA50'] and 30 < curr['RSI'] < 50:
                    direction = "SELL 🔴"
                    if curr['Volume'] > (avg_vol * 2.0): score += 1
                    if 35 <= curr['RSI'] <= 45: score += 1
                    if (curr['EMA50'] - curr['Close']) / curr['EMA50'] < 0.05: score += 1

                if direction:
                    signals.append({
                        "Ticker": ticker, "Dir": direction, "Price": round(curr['Close'], 2),
                        "Score": f"{score}/3", "TP": round(curr['Close'] + (4 * curr['ATR']), 2),
                        "SL": round(curr['Close'] - (2 * curr['ATR']), 2)
                    })
            except: continue

        if signals:
            st.table(pd.DataFrame(signals))
        else:
            st.write("לא נמצאו איתותים כרגע.")
