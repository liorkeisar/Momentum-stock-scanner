import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="Scanner")

# רשימת המניות (קבוצה אחת מהירה)
tickers = ["NVDA", "AMD", "PLTR", "SOUN", "BBAI", "CLSK", "MSTR", "COIN", "MARA", "RIOT", "HOOD", "AFRM", "RIVN", "TSLA", "META"]

st.title("🏹 High-Speed Market Scanner")

@st.cache_data(ttl=60) # קריטי: שומר את הנתונים בזיכרון לדקה כדי לא להפיל את השרת
def load_data():
    return yf.download(tickers, period="5d", group_by='ticker', progress=False)

if st.button("🚀 רענן סריקה"):
    try:
        data = load_data()
        results = []
        for t in tickers:
            # חילוץ נתונים מותאם למבנה של yfinance
            df = data[t] if isinstance(data, pd.DataFrame) else data
            if df.empty or len(df) < 2: continue
            
            last = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-2])
            change = ((last - prev) / prev) * 100
            
            if change > 0: # מניות בעלייה
                results.append({"Ticker": t, "Price": round(last, 2), "Change %": round(change, 2)})
        
        st.dataframe(pd.DataFrame(results).sort_values("Change %", ascending=False), use_container_width=True)
    except Exception as e:
        st.error("שגיאת טעינה - נסה שוב בעוד רגע.")
import streamlit as st
import pandas as pd
import requests

st.title("🏹 Simple Market Scanner")

# רשימת מניות לבדיקה
tickers = ["NVDA", "AMD", "PLTR", "SOUN", "MSTR", "COIN", "TSLA", "META"]

def get_price(ticker):
    try:
        # שימוש ב-API פשוט יותר
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        prices = response['chart']['result'][0]['indicators']['quote'][0]['close']
        last = prices[-1]
        prev = prices[-2]
        change = ((last - prev) / prev) * 100
        return {"Ticker": ticker, "Price": round(last, 2), "Change %": round(change, 2)}
    except:
        return None

st.write("סורק מניות...")
data = [get_price(t) for t in tickers]
data = [d for d in data if d is not None]

if data:
    st.dataframe(pd.DataFrame(data), use_container_width=True)
else:
    st.error("לא ניתן למשוך נתונים. ייתכן שאתה חסום עקב מגבלות IP של הענן.")
