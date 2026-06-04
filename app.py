import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("Market Scanner - Nasdaq 100 & Major Indices")

# פונקציית רשימות המניות - כאן הרחבתי את נאסד"ק לכל המניות המובילות
def get_tickers(index):
    if index == "NASDAQ_ALL":
        # 100 המניות המובילות והסחירות ביותר בנאסד"ק
        return [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP",
            "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON",
            "AMAT", "QCOM", "BKNG", "ISRG", "VRTX", "MDLZ", "REGN", "LRCX", "PANW", "SNPS",
            "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT",
            "PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP",
            "AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR",
            "ON", "EXC", "MRVL", "CTSH", "EA", "CDNS", "ABNB", "CEG", "MDB", "VRSK",
            "FAST", "CSX", "DXCM", "ANSS", "FFIV", "SBAC", "ALGN", "EBAY", "SIRI", "ZBRA",
            "ILMN", "WBA", "JD", "BIDU", "PDD", "LCID", "ZM", "MRNA", "PYPL", "INTC"
        ]
    elif index == "SP500": 
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "JPM", "V"]
    elif index == "DJIA": 
        return ["AAPL", "MSFT", "GS", "HD", "JPM", "MCD", "MMM", "PG", "UNH", "WMT"]
    elif index == "MIDCAP400": 
        return ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE"]
    return ["AAPL", "MSFT"]

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        df['MA20'] = df['Close'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        df['Vol20'] = df['Volume'].rolling(20).mean()
        
        if scan_type == "REVERSAL":
            # תנאי היפוך: מחיר חצה את ממוצע 20 כלפי מעלה
            if df['Close'].iloc[-1] > df['MA20'].iloc[-1] and df['Close'].iloc[-2] < df['MA20'].iloc[-2]:
                return ticker
        elif scan_type == "BREAKOUT":
            # תנאי פריצה: מחיר שבר שיא של 20 יום עם נפח מסחר גבוה מהממוצע
            if df['Close'].iloc[-1] > df['High20'].iloc[-1] and df['Volume'].iloc[-1] > df['Vol20'].iloc[-1]:
                return ticker
    except: return None
    return None

# יצירת הטאבים - הטאב הראשון הוא כעת נאסד"ק המורחב
tabs = st.tabs(["NASDAQ ALL REV", "NASDAQ ALL BRK", "SP500 REV", "DOW REV", "MIDC REV", 
                "SP500 BRK", "DOW BRK", "MIDC BRK"])

params = [
    ("NASDAQ_ALL", "REVERSAL"), ("NASDAQ_ALL", "BREAKOUT"),
    ("SP500", "REVERSAL"), ("DJIA", "REVERSAL"), ("MIDCAP400", "REVERSAL"), 
    ("SP500", "BREAKOUT"), ("DJIA", "BREAKOUT"), ("MIDCAP400", "BREAKOUT")
]

for i, (idx, scn) in enumerate(params):
    with tabs[i]:
        if st.button(f"הפעל סריקה עבור {idx} - {scn}", key=f"btn_{i}"):
            with st.spinner(f"מנתח מניות... זה עשוי לקחת מספר שניות"):
                tickers = get_tickers(idx)
                # שימוש ב-10 עובדים במקביל כדי להאיץ את הסריקה של נאסד"ק
                with ThreadPoolExecutor(max_workers=10) as ex:
                    results = list(ex.map(lambda t: run_scanner(t, scn), tickers))
                found = [r for r in results if r]
                
                st.success("הסריקה הושלמה!")
                if found:
                    st.write("### 🎯 מניות שנמצאו עם איתות חיובי:")
                    st.success(", ".join(found))
                else:
                    st.info("לא נמצאו איתותים העונים על תנאי האסטרטגיה כרגע.")
