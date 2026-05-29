import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Momentum Pro Radar", layout="wide")

# --- תפריט צד (Sidebar) ---
st.sidebar.title("🏹 רדאר מומנטום")
search_symbol = st.sidebar.text_input("חיפוש מניה (למשל: NVDA):", "", key="unique_search_input").upper()
run_single = st.sidebar.button("🔍 נתח מניה זו", key="btn_single")
st.sidebar.markdown("---")
run_scanner = st.sidebar.button("🚀 הרץ סורק שוק מלא", key="btn_scanner")

target_stocks = ["NVDA", "AMD", "SMCI", "AVGO", "PLTR", "TSLA", "META", "AMZN", "COIN", "MSTR", "HOOD", "FSLR", "ARM", "SNOW", "PATH"]

def get_analysis(ticker):
    df = yf.download(ticker, period="100d", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))
    
    curr = df.iloc[-1]
    score = (1 if curr['Close'] > curr['EMA50'] else 0) + (1 if 50 < curr['RSI'] < 70 else 0)
    sl = curr['Close'] - (2 * df['ATR'].iloc[-1])
    tp = curr['Close'] + (4 * df['ATR'].iloc[-1])
    return df, {"Ticker": ticker, "Score": score, "Price": round(curr['Close'], 2), "SL": round(sl, 2), "TP": round(tp, 2)}

def render_chart(df, stats):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='מחיר'))
    fig.add_hline(y=stats['SL'], line_color="red", line_dash="dash", annotation_text="SL")
    fig.add_hline(y=stats['TP'], line_color="green", line_dash="dash", annotation_text="TP")
    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- לוגיקה ראשית ---
st.title("📈 Momentum Pro Radar")

if run_single and search_symbol:
    with st.spinner(f"מנתח את {search_symbol}..."):
        try:
            df, stats = get_analysis(search_symbol)
            col1, col2, col3 = st.columns(3)
            col1.metric("מחיר נוכחי", f"${stats['Price']}")
            col2.metric("ציון מומנטום", f"{stats['Score']}/2")
            col3.metric("סטופ לוס", f"${stats['SL']}")
            render_chart(df, stats)
        except Exception as e:
            st.error("לא נמצאה מניה. בדוק את הסימבול.")

elif run_scanner:
    with st.spinner("סורק שוק..."):
        results = []
        for t in target_stocks:
            try:
                _, stats = get_analysis(t)
                results.append(stats)
            except: continue
        st.table(pd.DataFrame(results).sort_values(by="Score", ascending=False))
else:
    st.info("בחר מניה לניתוח מהתפריט בצד או הרץ סריקה מלאה.")
