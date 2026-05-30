import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("Market Scanner - 8 Strategies")

# רשימות יציבות למניעת שגיאות
def get_tickers(index):
    if index == "SP500": return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "AMD", "ADBE"]
    if index == "DJIA": return ["AAPL", "MSFT", "GS", "HD", "JPM", "MCD", "MMM", "PG", "UNH", "V"]
    if index == "NASDAQ100": return ["AAPL", "MSFT", "NVDA", "AMD", "ADBE", "INTC", "CSCO", "PEP", "AVGO", "QCOM"]
    if index == "MIDCAP400": return ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE"]
    return ["AAPL", "MSFT"]

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        df['MA20'] = df['Close'].rolling(20).mean()
        
        if scan_type == "REVERSAL":
            # תנאי דוגמה להיפוך: סגירה מעל ממוצע 20
            if df['Close'].iloc[-1] > df['MA20'].iloc[-1] and df['Close'].iloc[-2] < df['MA20'].iloc[-2]:
                return ticker
        elif scan_type == "BREAKOUT":
            # תנאי דוגמה לפריצה: שיא חדש
            if df['Close'].iloc[-1] > df['High'].iloc[-50:-1].max():
                return ticker
    except: return None
    return None

# יצירת 8 טאבים
tabs = st.tabs(["SP500 REV", "DOW REV", "NASD REV", "MIDC REV", 
                "SP500 BRK", "DOW BRK", "NASD BRK", "MIDC BRK"])

params = [("SP500", "REVERSAL"), ("DJIA", "REVERSAL"), ("NASDAQ100", "REVERSAL"), ("MIDCAP400", "REVERSAL"), 
          ("SP500", "BREAKOUT"), ("DJIA", "BREAKOUT"), ("NASDAQ100", "BREAKOUT"), ("MIDCAP400", "BREAKOUT")]

for i, (idx, scn) in enumerate(params):
    with tabs[i]:
        if st.button(f"סרוק {idx} ({scn})", key=f"btn_{i}"):
            with st.spinner("סורק..."):
                tickers = get_tickers(idx)
                with ThreadPoolExecutor(max_workers=5) as ex:
                    results = list(ex.map(lambda t: run_scanner(t, scn), tickers))
                found = [r for r in results if r]
                st.write(f"תוצאות עבור {idx}:", found if found else "לא נמצאו איתותים.")
