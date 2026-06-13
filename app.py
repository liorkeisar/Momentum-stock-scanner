import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="TITAN: Market Cap Scanner")

def get_scan_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252: return None
        
        # 1. סינון טכני מהיר (קודם כל נבדוק אם יש בכלל פוטנציאל טכני)
        curr_price = df['Close'].iloc[-1]
        low_52w = df['Low'].rolling(252).min().iloc[-1]
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        bb_width = (df['STD20'].iloc[-1] * 4 / df['MA20'].iloc[-1]) * 100
        
        if not (curr_price <= (low_52w * 1.10) and bb_width < 10):
            return None
            
        # 2. סינון שווי שוק (רק אם עבר את הסינון הטכני!)
        # info הוא החלק הכבד, לכן הוא בסוף
        market_cap = stock.info.get('marketCap', 0)
        if market_cap < 300_000_000:
            return None
            
        return {'Ticker': ticker, 'Price': round(curr_price, 2), 'MarketCap_M': round(market_cap/1e6, 1)}
    except:
        return None

st.title("🛡️ TITAN: Precision Market Cap Scanner")
st.write("סורק מניות בשפל שנתי, התכווצות (Squeeze) ושווי שוק > 300M$")

if st.button("התחל סריקה"):
    # רשימה לדוגמה (ניתן להחליף ב-get_universe())
    universe = ["AAPL", "NVDA", "MSFT", "AMD", "TSLA", "META", "GOOGL", "AMZN", "NFLX", "INTC"]
    
    results = []
    with st.spinner("סורק מניות (זה לוקח זמן כי אנחנו בודקים שווי שוק)..."):
        for t in universe:
            res = get_scan_data(t)
            if res: results.append(res)
    
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.info("לא נמצאו מניות שעומדות בתנאים (כולל שווי שוק מעל 300M).")
