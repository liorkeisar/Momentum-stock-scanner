import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Pro Market Scanner", layout="wide")

# --- פונקציות עזר למשיכת מניות ---
@st.cache_data
def get_tickers(index):
    try:
        if index == "DJIA":
            return ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW", 
                    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", 
                    "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"]
        elif index == "SP500":
            return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        elif index == "NASDAQ100":
            tables = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')
            for t in tables:
                if 'Ticker' in t.columns: return t['Ticker'].tolist()
                if 'Symbol' in t.columns: return t['Symbol'].tolist()
        elif index == "MIDCAP400":
            return pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_400_companies')[0]['Symbol'].tolist()
    except: 
        pass
    return ["AAPL", "MSFT", "NVDA"] # גיבוי במקרה של שגיאת רשת

# --- מנוע הסריקה המחמיר ---
def run_scanner(ticker, scan_type):
    try:
        df = yf.Ticker(ticker).history(period="150d")
        if len(df) < 50: return None
        
        # חישוב אינדיקטורים בסיסיים
        df['MA20'] = df['Close'].rolling(20).mean()
        df['Vol20'] = df['Volume'].rolling(20).mean()
        df['High20'] = df['High'].rolling(20).max().shift(1)
        
        # חישוב MACD 
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

        if scan_type == "REVERSAL":
            df['BUY'] = (df['MACD'] > df['Signal_Line']) & (df['MACD'].shift(1) <= df['Signal_Line'].shift(1)) & (df['Close'] > df['MA20'])
            df['SELL'] = (df['MACD'] < df['Signal_Line']) & (df['MACD'].shift(1) >= df['Signal_Line'].shift(1))
        
        elif scan_type == "BREAKOUT":
            df['BUY'] = (df['Close'] > df['High20']) & (df['Volume'] > df['Vol20'] * 2)
            df['SELL'] = (df['Close'] < df['MA20']) & (df['Close'].shift(1) >= df['MA20'].shift(1))

        if df['BUY'].iloc[-1]:
            return ticker, df
    except: return None
    return None

# --- פונקציית הגרף המקצועי ---
def draw_chart(df, ticker, scan_type):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.7])

    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    buy_signals = df[df['BUY']]
    sell_signals = df[df['SELL']]

    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.98, mode='markers+text',
                             text=['BUY'] * len(buy_signals), textposition='bottom center',
                             marker=dict(color='#00ff00', size=12, symbol='triangle-up'), name='Buy'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['High'] * 1.02, mode='markers+text',
                             text=['SELL'] * len(sell_signals), textposition='top center',
                             marker=dict(color='#ff0000', size=12, symbol='triangle-down'), name='Sell'), row=1, col=1)

    colors = ['green' if row['Close'] >= row['Open'] else 'red' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, 
                      showlegend=False, margin=dict(l=20, r=20, t=50, b=20),
                      title=f"{ticker} - {scan_type} Strategy Analysis")
    return fig

# --- ממשק האפליקציה ---
st.title("⚡ Pro Market Scanner")

# הוספת הלשוניות החדשות
tabs = st.tabs([
    "🚀 SP500 (Rev)", "🏢 Dow (Rev)", "💻 Nasdaq (Rev)", "📈 MidCap (Rev)", 
    "🔥 SP500 (Break)", "📊 Dow (Break)", "🌐 Nasdaq (Break)", "🌟 MidCap (Break)"
])

def execute(index, scan_type):
    tickers = get_tickers(index)
    with st.spinner(f"סורק {len(tickers)} מניות... (מחפש התאמה מחמירה)"):
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda t: run_scanner(t, scan_type), tickers))
        
        found = False
        for res in results:
            if res:
                ticker, df = res
                with st.expander(f"✅ {ticker}"):
                    st.plotly_chart(draw_chart(df, ticker, scan_type), use_container_width=True)
                found = True
        if not found: st.warning("לא נמצאו איתותים אמינים היום.")

# חיבור הלשוניות לכפתורים ולפונקציות המתאימות
with tabs[0]:
    if st.button("סרוק SP500 להיפוך"): execute("SP500", "REVERSAL")
with tabs[1]:
    if st.button("סרוק Dow להיפוך"): execute("DJIA", "REVERSAL")
with tabs[2]:
    if st.button("סרוק Nasdaq להיפוך"): execute("NASDAQ100", "REVERSAL")
with tabs[3]:
    if st.button("סרוק MidCap להיפוך"): execute("MIDCAP400", "REVERSAL")

with tabs[4]:
    if st.button("סרוק SP500 לפריצה"): execute("SP500", "BREAKOUT")
with tabs[5]:
    if st.button("סרוק Dow לפריצה"): execute("DJIA", "BREAKOUT")
with tabs[6]:
    if st.button("סרוק Nasdaq לפריצה"): execute("NASDAQ100", "BREAKOUT")
with tabs[7]:
    if st.button("סרוק MidCap לפריצה"): execute("MIDCAP400", "BREAKOUT")
