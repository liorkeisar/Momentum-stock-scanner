import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# הגדרת דף
st.set_page_config(layout="wide", page_title="ATR Momentum Scanner")
st.title("🏹 Scored ATR Momentum Scanner")

# רשימת המניות שלך
target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC", "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN", "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "FSLR", "ENPH", "WMT", "TGT", "COST", "LLY", "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "META", "GOOGL", "SPOT", "ROKU", "DIS", "NFLX", "SNAP", "PINS", "TTD", "RBLX", "CMG", "CELH", "ELF", "LULU", "NKE", "SBUX", "MNST", "CAT", "DE", "GE", "BA", "UBER", "CIFR", "WEX", "PAYC", "PCTY", "RUN", "BLNK", "CHPT", "QS", "BE", "NEE", "GEV", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "JOBY", "ACHR", "LUNR", "RKLB", "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "EXAS", "NVAX", "EDIT", "BEAM", "NTLA", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL", "DRI", "TXRH", "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "LYFT"]

if st.button("🚀 הרץ סריקת ATR מומנטום"):
    with st.spinner("סורק מניות ומחשב ציוני איכות..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        signals = []

        for ticker in target_stocks:
            try:
                data = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
                if len(data) < 60: continue

                # אינדיקטורים
                data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
                delta = data['Close'].diff()
                data['RSI'] = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean() / (-delta.where(delta < 0, 0).rolling(14).mean() + 1e-9))))
                
                tr = pd.concat([data['High']-data['Low'], abs(data['High']-data['Close'].shift()), abs(data['Low']-data['Close'].shift())], axis=1).max(axis=1)
                data['ATR'] = tr.rolling(14).mean()

                curr = data.iloc[-1]
                highest_20 = data['High'].iloc[-21:-1].max()
                lowest_20 = data['Low'].iloc[-21:-1].min()
                avg_vol = data['Volume'].iloc[-21:-1].mean()

                # לוגיקה שלך לאיתותים
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
                        "Ticker": ticker, "Direction": direction, "Price": round(curr['Close'], 2),
                        "Score": f"{score}/3", "TP": round(curr['Close'] + (4 * data['ATR'].iloc[-1]), 2),
                        "SL": round(curr['Close'] - (2 * data['ATR'].iloc[-1]), 2)
                    })
            except: continue

        if signals:
            st.table(pd.DataFrame(signals))
        else:
            st.info("לא נמצאו איתותים כרגע.")
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Momentum Pro Radar")

st.title("🏹 Scored ATR Momentum Pro Radar")
st.markdown("סורק מניות עם דירוג איכות, ממוין לפי עוצמת המומנטום.")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR"]

if st.button("🚀 הרץ סריקת מומנטום מלאה"):
    with st.spinner("סורק ומדרג..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        results = []

        for ticker in target_stocks:
            try:
                df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
                
                # חישובים טכניים
                df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
                df['ATR'] = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1).rolling(14).mean()
                
                curr = df.iloc[-1]
                highest_20 = df['High'].iloc[-21:-1].max()
                
                # ציון איכות (Score)
                score = 0
                if curr['Close'] > highest_20: score += 1
                if curr['Close'] > curr['EMA50']: score += 1
                if curr['Volume'] > df['Volume'].iloc[-21:-1].mean(): score += 1
                
                results.append({
                    "Ticker": ticker,
                    "Score": score,
                    "Price": round(curr['Close'], 2),
                    "SL": round(curr['Close'] - (2 * df['ATR'].iloc[-1]), 2),
                    "TP": round(curr['Close'] + (4 * df['ATR'].iloc[-1]), 2),
                    "ATR": round(df['ATR'].iloc[-1], 2)
                })
            except: continue

        # יצירת טבלה אינטראקטיבית ממוינת לפי ציון (Score)
        df_final = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        
        # הצגת הטבלה
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        # בחירת מניה לניתוח עומק
        selected = st.selectbox("בחר מניה מהטבלה לצפייה בגרף:", df_final['Ticker'].tolist())
        
        # גרף נרות מקצועי
        df_plot = yf.download(selected, period="6mo", progress=False)
        if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
        
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
