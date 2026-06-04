import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("Quantum Terminal - Maximum Sectional Scanner")

# --- מאגר מניות מורחב למקסימום ומחולק ל-8 קבוצות יציבות ---
def get_sectional_tickers(section_name):
    # נאסד"ק 100 מלא - מחולק ל-4 קבוצות של 25 מניות
    if section_name == "NASDAQ_A":
        return ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON", "AMAT", "QCOM", "BKNG", "ISRG", "VRTX"]
    elif section_name == "NASDAQ_B":
        return ["MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT", "PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP"]
    elif section_name == "NASDAQ_C":
        return ["AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR", "ON", "EXC", "MRVL", "CTSH", "EA", "CDNS", "ABNB", "CEG", "MDB", "VRSK", "FAST", "CSX", "DXCM", "ANSS", "FFIV"]
    elif section_name == "NASDAQ_D":
        return ["SBAC", "ALGN", "EBAY", "SIRI", "ZBRA", "ILMN", "WBA", "JD", "BIDU", "LCID", "ZM", "MRNA", "PYPL", "INTC", "ADX", "ALXN", "ATVI", "BIIB", "CHKP", "DLTR", "EXPE", "FISV", "LULU", "MU", "XLNX"]
    
    # S&P 500 - מחולק ל-2 קבוצות גדולות (כ-60 מניות מובילות שוק)
    elif section_name == "SP500_A":
        return ["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "BRK.B", "TSLA", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "LLY", "COST", "PEP", "ADBE", "WMT", "MCD", "CSCO", "CRM", "BAC"]
    elif section_name == "SP500_B":
        return ["ACN", "TMO", "LIN", "ORCL", "AMD", "CMCSA", "ABT", "TXN", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "GE", "AXP", "T", "DHR", "PLD", "SBUX", "CAT", "BA", "DE", "ISRG", "HON", "LOW", "SPGI", "BLK", "NOW"]
    
    # דאו ג'ונס - כל 30 המניות ללא יוצא מן הכלל
    elif section_name == "DOW_FULL":
        return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
    
    # MidCap 400 - קבוצה נבחרת של המניות התנודתיות ביותר במדד
    elif section_name == "MIDCAP":
        return ["FDS", "PNR", "RS", "TKO", "POOL", "WSO", "ELF", "JBL", "MTH", "CBOE", "XYL", "HAE", "AAL", "TEX", "MTD", "WFR", "LANC", "OLLIE", "CHDN", "SAIA", "TREX", "YETI", "CROX", "DECK", "SKX", "LOPE", "GDDY", "BLD", "FIX", "AOS"]
    
    return ["AAPL", "MSFT"]

def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="100d")
        if len(df) < 50: return None
        df['MA20'] = df['Close'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        df['Vol20'] = df['Volume'].rolling(20).mean()
        
        if scan_type == "REVERSAL":
            if df['Close'].iloc[-1] > df['MA20'].iloc[-1] and df['Close'].iloc[-2] < df['MA20'].iloc[-2]:
                return ticker
        elif scan_type == "BREAKOUT":
            if df['Close'].iloc[-1] > df['High20'].iloc[-1] and df['Volume'].iloc[-1] > df['Vol20'].iloc[-1]:
                return ticker
    except: return None
    return None

# --- יצירת 8 הלשוניות בממשק ---
tabs = st.tabs([
    "NASDAQ א'", "NASDAQ ב'", "NASDAQ ג'", "NASDAQ ד'", 
    "S&P500 א'", "S&P500 ב'", 
    "DOW מלא", "MIDCAP 400"
])

sections = [
    ("NASDAQ_A", "נאסדק קבוצה א'"), ("NASDAQ_B", "נאסדק קבוצה ב'"), 
    ("NASDAQ_C", "נאסדק קבוצה ג'"), ("NASDAQ_D", "נאסדק קבוצה ד'"),
    ("SP500_A", "S&P קבוצה א'"), ("SP500_B", "S&P קבוצה ב'"),
    ("DOW_FULL", "דאו ג'ונס מלא"), ("MIDCAP", "מיד-קאפ 400")
]

for i, (group_id, label) in enumerate(sections):
    with tabs[i]:
        st.subheader(f"🖥️ סורק ממוקד: {label}")
        
        mode = st.radio("בחר אסטרטגיה:", ["REVERSAL", "BREAKOUT"], key=f"radio_{i}")
        
        if st.button(f"הפעל סריקה", key=f"btn_{i}"):
            with st.spinner("מנתח נתוני שוק בזמן אמת..."):
                tickers = get_sectional_tickers(group_id)
                
                # סריקה במקביל של 10 מניות בו זמנית לביצועים מהירים
                with ThreadPoolExecutor(max_workers=10) as ex:
                    results = list(ex.map(lambda t: run_scanner(t, mode), tickers))
                
                found = [r for r in results if r]
                
                st.success("הסריקה הסתיימה בהצלחה!")
                if found:
                    st.write("### 🎯 מניות שעונות על תנאי האלגוריתם כרגע:")
                    st.success(", ".join(found))
                else:
                    st.info("לא אותרו הזדמנויות מסחר בקבוצה זו תחת התנאים שנבחרו.")
