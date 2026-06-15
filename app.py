import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# הגדרות עיצוב
st.set_page_config(layout="wide", page_title="סורק הצטברות מניות")

# רשימת הטיקרים (העתקתי את הרשימה שלך מהסקריפט)
TICKERS = ["AAPL", "MSFT", "NVDA", "AMD", "INTC", "QCOM", "MU", "AVGO", "TXN", "AMAT", "GOOGL", "META", "NFLX", "SNAP", "PINS", "ZM", "ROKU", "UBER", "LYFT", "TWLO", "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "COF", "SCHW", "AXP", "JNJ", "PFE", "MRK", "ABBV", "BMY", "LLY", "CVS", "AMGN", "GILD", "BIIB", "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "OXY", "HAL", "DVN", "FANG", "WMT", "TGT", "COST", "HD", "LOW", "NKE", "SBUX", "MCD", "YUM", "DPZ", "BA", "CAT", "GE", "MMM", "HON", "RTX", "LMT", "NOC", "GD", "DE", "FCX", "NEM", "AA", "CLF", "X", "NUE", "STLD", "ALB", "MP", "CCJ", "NEE", "DUK", "SO", "AEP", "EXC", "D", "PCG", "ETR", "NRG", "AES", "AMT", "PLD", "CCI", "EQIX", "PSA", "EXR", "AVB", "EQR", "VTR", "O", "TSLA", "F", "GM", "RIVN", "NIO", "LI", "XPEV", "LCID", "FSR", "PYPL", "SQ", "AFRM", "UPST", "SOFI", "HOOD", "MKTX", "IBKR", "DFS", "CRM", "NOW", "WDAY", "ADBE", "INTU", "VEEV", "HUBS", "MDB", "DDOG", "PLTR", "ZS", "CRWD", "S", "PANW", "FTNT", "CYBR", "TENB", "QLYS", "VRNT", "CHKP", "ORCL", "IBM", "SNOW", "CSCO", "HPQ", "DELL", "STX", "WDC", "NTAP", "PSTG", "LUV", "DAL", "UAL", "AAL", "JBLU", "ALK", "MAR", "HLT", "H", "CHH", "UPS", "FDX", "XPO", "SAIA", "ODFL", "WERN", "JBHT", "KNX", "CHRW", "EXPD", "AMRN", "ACAD", "SAGE", "AXSM", "REGN", "VRTX", "MRNA", "BNTX", "ILMN", "TDOC", "FSLR", "ENPH", "SEDG", "NOVA", "RUN", "ARRY", "CSIQ", "JKS", "DAQO", "HASI"]

def get_analysis(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if len(df) < 30: return None
        
        # אינדיקטורים
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        adx = ta.adx(df['High'], df['Low'], df['Close'])
        df = pd.concat([df, adx], axis=1)
        
        # חישוב לוגיקת סקור בסיסית
        score = 0
        if df['RSI'].iloc[-1] < 40: score += 20
        if df['MACD_12_26_9'].iloc[-1] > df['MACDs_12_26_9'].iloc[-1]: score += 20
        
        return {
            "Ticker": ticker,
            "Price": float(df['Close'].iloc[-1]),
            "RSI": float(df['RSI'].iloc[-1]),
            "Score": score,
            "Pattern": "Sideways" if df['ADX_14'].iloc[-1] < 20 else "Trending"
        }
    except:
        return None

# ממשק משתמש
st.title("◈ סורק הצטברות מניות")

if st.button("התחל סריקה"):
    results = []
    bar = st.progress(0)
    for i, ticker in enumerate(TICKERS):
        res = get_analysis(ticker)
        if res: results.append(res)
        bar.progress((i + 1) / len(TICKERS))
    
    df_results = pd.DataFrame(results)
    st.dataframe(df_results.sort_values(by="Score", ascending=False), use_container_width=True)
    
    # ויזואליזציה פשוטה של המניה הראשונה שנמצאה
    if not df_results.empty:
        st.subheader(f"גרף למניה מובילה: {df_results.iloc[0]['Ticker']}")
        st.line_chart(yf.download(df_results.iloc[0]['Ticker'], period="3mo")['Close'])
