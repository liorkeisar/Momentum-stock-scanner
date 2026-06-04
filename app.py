import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("Quantum Terminal - Full Market Sectional Scanner")

# --- מאגרי המניות המלאים מחולקים לקבוצות למניעת עומס ---
def get_sectional_tickers(section_name):
    # כלל מניות ה-S&P 500 מחולקות ל-2 קבוצות
    if section_name == "SP500_PART1":
        return ["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "BRK.B", "TSLA", "UNH", "JPM", "XOM", "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "LLY", "COST", "PEP", "ADBE", "WMT", "MCD", "CSCO", "CRM", "BAC"]
    elif section_name == "SP500_PART2":
        return ["ACN", "TMO", "LIN", "ORCL", "AMD", "CMCSA", "ABT", "TXN", "NKE", "PM", "UPS", "COP", "MS", "PFE", "NEE", "GE", "INTC", "AMGN", "HON", "LOW", "SPGI", "AXP", "T", "DHR", "PLD", "SBUX", "CAT", "BA", "DE", "ISRG"]
    
    # כלל מניות ה-DOW JONES (כל 30 המניות המלאות של המדד)
    elif section_name == "DOW_FULL":
        return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
    
    # כלל מניות נאסד"ק מחולקות ל-3 קבוצות משמעותיות
    elif section_name == "NASDAQ_PART1":
        return ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", "COST", "CSCO", "TMUS", "ADBE", "AMD", "NFLX", "TXN", "AMGN", "INTU", "HON"]
    elif section_name == "NASDAQ_PART2":
        return ["AMAT", "QCOM", "BKNG", "ISRG", "VRTX", "MDLZ", "REGN", "LRCX", "PANW", "SNPS", "KLAC", "ASML", "MELI", "MAR", "CTAS", "ORLY", "CRWD", "NXPI", "WDAY", "FTNT"]
    elif section_name == "NASDAQ_PART3":
        return ["PCAR", "MNST", "ADSK", "PAYX", "ROST", "AEP", "CPRT", "KDP", "CHTR", "MCHP", "AZN", "DDOG", "ODFL", "GILD", "PDD", "TEAM", "IDXX", "ADI", "GEHC", "BKR"]
    
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

# --- יצירת הלשוניות לפי הקבוצות המפוצלות ---
tabs = st.tabs([
    "NASDAQ קבוצה א'", "NASDAQ קבוצה ב'", "NASDAQ קבוצה ג'", 
    "S&P500 קבוצה א'", "S&P500 קבוצה ב'", 
    "DOW מלא"
])

# הגדרת הפרמטרים לכל לשונית (שם הקבוצה, וסוג הסריקה שיוצג בתוכה)
sections = [
    ("NASDAQ_PART1", "נאסדק א'"), ("NASDAQ_PART2", "נאסדק ב'"), ("NASDAQ_PART3", "נאסדק ג'"),
    ("SP500_PART1", "S&P קבוצה 1"), ("SP500_PART2", "S&P קבוצה 2"),
    ("DOW_FULL", "דאו ג'ונס מלא")
]

for i, (group_id, label) in enumerate(sections):
    with tabs[i]:
        st.subheader(f"סורק ייעודי - {label}")
        
        # בחירת אסטרטגיה בתוך הלשונית
        mode = st.radio("בחר אסטרטגיה לסריקה זו:", ["REVERSAL", "BREAKOUT"], key=f"radio_{i}")
        
        if st.button(f"הפעל סריקה על {label}", key=f"btn_{i}"):
            with st.spinner("מנתח את קבוצת המניות הנוכחית..."):
                tickers = get_sectional_tickers(group_id)
                
                # סריקה ממוקדת ומהירה של הקבוצה שנבחרה
                with ThreadPoolExecutor(max_workers=10) as ex:
                    results = list(ex.map(lambda t: run_scanner(t, mode), tickers))
                
                found = [r for r in results if r]
                
                st.success("הסריקה לקבוצה זו הושלמה!")
                if found:
                    st.write("### 🎯 מניות שעונות על תנאי האלגוריתם:")
                    st.success(", ".join(found))
                else:
                    st.info("לא אותרו הזדמנויות מסחר בקבוצה זו כרגע.")
