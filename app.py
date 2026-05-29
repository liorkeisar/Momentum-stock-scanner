import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(layout="wide", page_title="Pro Trader Radar")
st.title("🏹 Momentum Pro Radar")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC", "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN", "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "FSLR", "ENPH", "WMT", "TGT", "COST", "LLY", "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "META", "GOOGL", "SPOT", "ROKU", "DIS", "NFLX", "SNAP", "PINS", "TTD", "RBLX", "CMG", "CELH", "ELF", "LULU", "NKE", "SBUX", "MNST", "CAT", "DE", "GE", "BA", "UBER", "CIFR", "WEX", "PAYC", "PCTY", "RUN", "BLNK", "CHPT", "QS", "BE", "NEE", "GEV", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "JOBY", "ACHR", "LUNR", "RKLB", "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "EXAS", "NVAX", "EDIT", "BEAM", "NTLA", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL", "DRI", "TXRH", "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "LYFT"]

if st.button("🚀 הרץ סריקה מקיפה"):
    results = []
    all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)

    for ticker in target_stocks:
        if ticker not in all_data.columns.levels[0]: continue
        
        df = all_data[ticker].dropna()
        if len(df) < 60: continue
        
        # חישובים טכניים
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # ATR
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # לוגיקת איתותים
        curr = df.iloc[-1]
        hist = df.iloc[:-1]
        if (curr['Close'] > hist['High'].tail(20).max() and curr['Volume'] > hist['Volume'].tail(20).mean() * 1.2 and curr['Close'] > curr['EMA50']):
            results.append({"ticker": ticker, "type": "BUY", "price": curr['Close'], "atr": curr['ATR']})
        elif (curr['Close'] < hist['Low'].tail(20).min() and curr['Volume'] > hist['Volume'].tail(20).mean() * 1.2 and curr['Close'] < curr['EMA50']):
            results.append({"ticker": ticker, "type": "SELL", "price": curr['Close'], "atr": curr['ATR']})

    st.success(f"נמצאו {len(results)} איתותים!")

    for res in results:
        with st.expander(f"{res['ticker']} - {res['type']} - ${res['price']:.2f}"):
            # הכנה לגרף
            df_plot = yf.download(res['ticker'], period="1mo", interval="1d", progress=False)
            if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
            df_plot = df_plot.reset_index()
            
            chart_data = [{"time": str(r['Date']).split(' ')[0], "open": float(r['Open']), "high": float(r['High']), "low": float(r['Low']), "close": float(r['Close'])} for _, r in df_plot.iterrows()]
            
            renderLightweightCharts([{"chart": {"height": 300, "layout": {"background": {"color": "#0E1117"}, "textColor": "#DDD"}}, "series": [{"type": "Candlestick", "data": chart_data}]}], res['ticker'])
            import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

# ... (שאר הקוד של הסריקה נשאר כפי שהיה עד הלולאה) ...

    # בתוך לולאת הצגת התוצאות:
    for res in results:
        with st.expander(f"{res['ticker']} - {res['type']} - ${res['price']:.2f}"):
            # הוספת "טוען" כדי שיהיה חיווי ויזואלי
            with st.spinner(f"טוען גרף עבור {res['ticker']}..."):
                df_plot = yf.download(res['ticker'], period="1mo", interval="1d", progress=False)
                if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
                df_plot = df_plot.reset_index()
                
                chart_data = [{"time": str(r['Date']).split(' ')[0], "open": float(r['Open']), 
                               "high": float(r['High']), "low": float(r['Low']), "close": float(r['Close'])} 
                              for _, r in df_plot.iterrows()]
                
                renderLightweightCharts([{"chart": {"height": 300, "layout": {"background": {"color": "#0E1117"}, "textColor": "#DDD"}}, 
                                        "series": [{"type": "Candlestick", "data": chart_data}]}], res['ticker'])

