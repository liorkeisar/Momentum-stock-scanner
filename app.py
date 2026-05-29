import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏹 Momentum Pro Radar - סורק מניות מקצועי")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "ASML", "MU", "LRCX", "AMAT", "PLTR", "SOUN", "BBAI", "AI", "INTC", "QCOM", "TXN", "ADI", "MRVL", "KLAC", "SNPS", "CDNS", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "WDAY", "TEAM", "MDB", "ZS", "OKTA", "PATH", "NOW", "ORCL", "CRM", "HUBS", "ANET", "COIN", "MARA", "RIOT", "CLSK", "MSTR", "WULF", "HOOD", "SQ", "PYPL", "AFRM", "SOFI", "UPST", "COF", "NU", "MELI", "SE", "SHOP", "CHWY", "AMZN", "TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "FSLR", "ENPH", "WMT", "TGT", "COST", "LLY", "NVO", "MRNA", "CRSP", "BNTX", "VRTX", "AMGN", "GILD", "REGN", "META", "GOOGL", "SPOT", "ROKU", "DIS", "NFLX", "SNAP", "PINS", "TTD", "RBLX", "CMG", "CELH", "ELF", "LULU", "NKE", "SBUX", "MNST", "CAT", "DE", "GE", "BA", "UBER", "CIFR", "WEX", "PAYC", "PCTY", "RUN", "BLNK", "CHPT", "QS", "BE", "NEE", "GEV", "SEDG", "CSIQ", "ARRY", "SHLS", "STEM", "JOBY", "ACHR", "LUNR", "RKLB", "TCOM", "W", "ANF", "GAP", "URBN", "JWN", "EXAS", "NVAX", "EDIT", "BEAM", "NTLA", "LYV", "NYT", "WMG", "IMAX", "AMC", "SKX", "TPR", "PVH", "RL", "DRI", "TXRH", "UAL", "AAL", "DAL", "LUV", "RCL", "CCL", "NCLH", "LYFT"]

if st.button("🚀 הרץ סריקה מקיפה"):
    with st.spinner("מנתח מניות..."):
        all_data = yf.download(target_stocks, period="100d", group_by='ticker', progress=False)
        
        for ticker in target_stocks:
            data = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
            if len(data) < 60: continue
            
            # חישובי אינדיקטורים
            data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
            tr = pd.concat([data['High']-data['Low'], abs(data['High']-data['Close'].shift()), abs(data['Low']-data['Close'].shift())], axis=1).max(axis=1)
            data['ATR'] = tr.rolling(14).mean()
            
            curr = data.iloc[-1]
            if curr['Close'] > curr['EMA50']:
                sl = curr['Close'] - (2 * curr['ATR'])
                tp = curr['Close'] + (4 * curr['ATR'])
                
                # תצוגה
                st.write(f"---")
                st.subheader(f"{ticker} | BUY")
                st.write(f"סטופ: **${sl:.2f}** | יעד: **${tp:.2f}**")
                
                fig = go.Figure(data=[go.Candlestick(x=data.index[-30:], open=data['Open'][-30:], high=data['High'][-30:], low=data['Low'][-30:], close=data['Close'][-30:])])
                fig.add_hline(y=sl, line_color="red", line_dash="dash")
                fig.add_hline(y=tp, line_color="green", line_dash="dash")
                fig.update_layout(template="plotly_white", height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig, use_container_width=True)
                import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Pro Momentum Radar")
st.title("🏹 Momentum Pro Radar - Dashboard")

# רשימת המניות (קצרתי חלק כדי להאיץ את הטעינה בטלפון)
target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "AAPL", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR"]

if st.button("🚀 סרוק שוק"):
    results = []
    all_data = yf.download(target_stocks, period="60d", group_by='ticker', progress=False)
    
    for ticker in target_stocks:
        df = all_data[ticker].dropna() if isinstance(all_data.columns, pd.MultiIndex) else all_data.dropna()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        
        # חישוב איתות פשוט להצגה בטבלה
        last_close = df['Close'].iloc[-1]
        ema = df['EMA50'].iloc[-1]
        signal = "BUY" if last_close > ema else "WAIT"
        
        results.append({"Ticker": ticker, "Price": round(last_close, 2), "Signal": signal, "EMA50": round(ema, 2)})

    # הפיכה לטבלה בסגנון Investing
    df_results = pd.DataFrame(results)
    st.table(df_results)
    
    # בחירת מניה מהרשימה להצגת גרף
    selected_ticker = st.selectbox("בחר מניה מהרשימה לניתוח טכני מעמיק:", df_results['Ticker'].tolist())
    
    # הצגת הגרף למניה שנבחרה בלבד
    st.subheader(f"ניתוח טכני: {selected_ticker}")
    df_plot = yf.download(selected_ticker, period="3mo", interval="1d", progress=False)
    fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
    fig.update_layout(template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)

