import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os

# --- הגדרות עמוד ---
st.set_page_config(page_title="Institutional Scanner Pro", layout="wide")

# --- 1. מנוע חישובים וניתוח ---
def calculate_all(df, market_df):
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    df['Is_Spike'] = df['Volume'] > (df['Volume'].rolling(20).mean() * 2)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Divergence'] = (df['Close'] <= df['Close'].rolling(20).min()) & (df['MACD'] > df['MACD'].rolling(20).min())
    df['RS'] = (df['Close'] / df['Close'].iloc[0]) / (market_df['Close'] / market_df['Close'].iloc[0])
    return df

def get_ai_analysis(ticker, data):
    last = data.iloc[-1]
    reasons = []
    if last['Divergence']: reasons.append("זוהתה דיברגנציה שורית ב-MACD (סימן להיפוך פוטנציאלי)")
    if last['Close'] > last['VWAP']: reasons.append("המחיר נסגר מעל ה-VWAP (עדות לצבירה מוסדית)")
    if last['Is_Spike']: reasons.append("נצפתה קפיצה חריגה במחזור המסחר (עניין מוגבר)")
    if last['RS'] > 1.0: reasons.append("המניה מציגה ביצועי יתר (Relative Strength) מול השוק")
    
    if not reasons: return "לא נמצאו אינדיקטורים חזקים מספיק לניתוח מעמיק ברגע זה."
    return f"**מדוע {ticker} נבחרה:** " + " | ".join(reasons) + "."

# --- 2. ממשק משתמש ---
st.title("🛡️ Institutional Accumulation Scanner")

# סרגל צד
with st.sidebar:
    st.header("⚙️ הגדרות סריקה")
    available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    index_option = st.selectbox("בחר קובץ רשימת מניות:", available_files) if available_files else st.error("לא נמצאו קבצי CSV")
    run_btn = st.button("🚀 הרץ סריקה", type="primary")

tabs = st.tabs(["🔍 סורק פעיל", "📁 ארכיון תוצאות"])

with tabs[0]:
    if run_btn and available_files:
        st.session_state['results'] = {}
        tickers = pd.read_csv(index_option, header=None)[0].tolist()
        market_df = yf.Ticker("SPY").history(period="1y")
        
        progress_bar = st.progress(0)
        with st.spinner('מנתח מניות...'):
            for i, ticker in enumerate(tickers):
                progress_bar.progress((i + 1) / len(tickers))
                try:
                    df = yf.Ticker(ticker.strip()).history(period="1y")
                    if len(df) > 50:
                        df = calculate_all(df, market_df.iloc[-len(df):])
                        if df.iloc[-1]['Divergence'] and df.iloc[-1]['Close'] > df.iloc[-1]['VWAP']:
                            st.session_state['results'][ticker] = df
                except: continue
        
        with open('scanner_history.json', 'w') as f:
            json.dump(list(st.session_state['results'].keys()), f)
        st.success("הסריקה הסתיימה!")

    if 'results' in st.session_state and st.session_state['results']:
        col_left, col_right = st.columns([1, 2])
        with col_left:
            selected_ticker = st.selectbox("בחר מניה מהתוצאות:", list(st.session_state['results'].keys()))
            st.session_state['selected'] = selected_ticker
            
            # ניתוח AI
            st.info(get_ai_analysis(selected_ticker, st.session_state['results'][selected_ticker]))
            
            last = st.session_state['results'][selected_ticker].iloc[-1]
            st.markdown("### 📊 סטטוס טכני נוכחי")
            c1, c2 = st.columns(2)
            c1.metric("RSI", round(last['RSI'], 2))
            c2.metric("RS (Relative Strength)", round(last['RS'], 2))

        with col_right:
            df = st.session_state['results'][st.session_state['selected']]
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name='VWAP', line=dict(color='yellow', width=1.5)))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("📁 ארכיון מניות שנסרקו")
    if os.path.exists('scanner_history.json'):
        with open('scanner_history.json', 'r') as f:
            history = json.load(f)
        
        if not history:
            st.info("הארכיון ריק.")
        else:
            cols = st.columns(4)
            for i, ticker in enumerate(history):
                with cols[i % 4]:
                    with st.container(border=True):
                        st.markdown(f"### 📈 {ticker}")
                        st.write("מניה שעברה סינון מוסדי")
