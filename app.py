import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import os
import json
from datetime import datetime

st.set_page_config(page_title="סורק איסוף מוסדי Pro", layout="wide")
st.title("🛡️ סורק איסוף מוסדי - Pro")

# --- פונקציות עזר (ללא שינוי) ---
@st.cache_data
def load_tickers(filename):
    try:
        df = pd.read_csv(filename, header=None)
        return df[0].dropna().tolist()
    except Exception as e:
        st.error(f"שגיאה בטעינת {filename}: {e}")
        return []

@st.cache_data
def get_market_data():
    spy = yf.Ticker("SPY").history(period="1y")
    return spy['Close']

def calculate_indicators(df):
    # VWAP
    q = df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)
    df['VWAP'] = q.cumsum() / df['Volume'].cumsum()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    # MFI
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    mf = typical * df['Volume']
    pos = mf.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg = mf.where(typical < typical.shift(1), 0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos / neg)))
    # Bollinger & Averages
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Width'] = ((df['MA20'] + (std20 * 2) - (df['MA20'] - (std20 * 2))) / df['MA20']) * 100
    return df

# --- אתחול Session State ---
if 'results_cache' not in st.session_state: st.session_state['results_cache'] = {}
if 'found_stocks' not in st.session_state: st.session_state['found_stocks'] = []

# --- תפריט צדדי ---
st.sidebar.header("בקרת סריקה")
# הפיצ'ר החדש: הכנסת מניה ידנית
manual_ticker = st.sidebar.text_input("הכנס מניה לבדיקה ידנית (למשל: AAPL):")

available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
index_option = st.sidebar.selectbox("בחר רשימת מניות לסריקה:", available_files)

# --- כפתור הסריקה ---
if st.sidebar.button('🚀 הרץ סריקה'):
    found = []
    market_data = get_market_data()
    
    # לוגיקה לבחירת המניות לסריקה
    if manual_ticker:
        # אם הוכנסה מניה ידנית, נסרוק רק אותה
        ticker_list = [manual_ticker.upper()]
        st.sidebar.info(f"מריץ בדיקה ידנית על {manual_ticker.upper()}")
    else:
        # אחרת, נסרוק את הרשימה מהקובץ
        ticker_list = load_tickers(index_option)
        st.sidebar.info(f"מריץ סריקה על {len(ticker_list)} מניות מתוך {index_option}")

    progress_bar = st.progress(0)
    
    # ניקוי זיכרון cache לפני סריקה חדשה
    st.session_state['results_cache'] = {}
    
    for i, ticker in enumerate(ticker_list):
        try:
            time.sleep(0.05) # מניעת חסימה
            df = yf.Ticker(ticker).history(period="1y")
            if len(df) < 60: continue
            df = calculate_indicators(df)
            last = df.iloc[-1]
            # RS Calculation
            rs_score = (last['Close'] / df['Close'].iloc[-20]) / (market_data.iloc[-1] / market_data.iloc[-20])
            
            # --- הלוגיקה המקצועית לאיסוף מוסדי ---
            if (last['Close'] < (df['Low'].tail(252).min() * 1.15) and 
                last['Close'] > last['MA50'] and 
                last['Close'] > (last['VWAP'] * 1.01) and
                last['BB_Width'] < 10 and 
                40 < last['RSI'] < 65 and 
                last['MFI'] > 50 and
                rs_score > 1.0):
                found.append(ticker)
                st.session_state['results_cache'][ticker] = df
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    # עדכון Session State
    st.session_state['found_stocks'] = found
    
    # אם נסרקה רשימה (לא מניה בודדת), נשמור אותה כ"סריקה שמורה"
    if not manual_ticker:
        with open('latest_results.json', 'w') as f:
            json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "stocks": found}, f)
        st.success(f"סריקת הרשימה הסתיימה! נמצאו {len(found)} מניות איכותיות.")
    else:
        if found:
            st.success(f"המניה {manual_ticker.upper()} עומדת בקריטריונים של איסוף מוסדי!")
        else:
            st.warning(f"המניה {manual_ticker.upper()} אינה עומדת בקריטריונים כרגע.")

# --- לשוניות תצוגה ---
# הכל הוחזר למקומו
tab1, tab2, tab3 = st.tabs(["🎯 סריקה חיה", "📊 כל נתוני המדד", "📅 סריקה שמורה"])

with tab1:
    st.subheader("תוצאות הסריקה האחרונה")
    if 'found_stocks' in st.session_state and st.session_state['found_stocks']:
        selected = st.selectbox("בחר מניה לתצוגה:", st.session_state['found_stocks'])
        if selected in st.session_state['results_cache']:
            df = st.session_state['results_cache'][selected]
            
            # גרף נרות
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='מחיר')])
            # קו VWAP (צהוב)
            fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'))
            # חץ ירוק לקניה
            fig.add_trace(go.Scatter(
                x=[df.index[-1]], y=[df['Low'].iloc[-1] * 0.98],
                mode='markers',
                marker=dict(symbol='triangle-up', size=20, color='lime'),
                name='אות קניה (אישור סורק)'
            ))
            
            fig.update_layout(template="plotly_dark", title=f"גרף: {selected} - איתות קניה", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("המידע עבור מניה זו לא זמין. בצע סריקה.")
    else:
        st.info("אנא בצע סריקה כדי לראות תוצאות.")

with tab2:
    st.subheader("כל הנתונים הגולמיים")
    # כאן אפשר להוסיף טבלה של כל המניות שנסרקו עם האינדיקטורים שלהן
    if 'results_cache' in st.session_state and st.session_state['results_cache']:
        # יצירת DataFrame מהתוצאות בזיכרון
        data = []
        for ticker, df in st.session_state['results_cache'].items():
            last = df.iloc[-1]
            data.append({
                'Ticker': ticker,
                'Close': round(last['Close'], 2),
                'RSI': round(last['RSI'], 1),
                'MFI': round(last['MFI'], 1),
                'BB_Width': round(last['BB_Width'], 1)
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("בצע סריקה כדי להציג נתונים.")

with tab3:
    st.subheader("תוצאות סוף השבוע / סריקה אחרונה שמורה")
    # הלשונית שקוראת מהקובץJSON
    if os.path.exists('latest_results.json'):
        with open('latest_results.json', 'r') as f:
            saved = json.load(f)
            st.write(f"תאריך הסריקה: {saved['date']}")
            st.write(f"מניות שנמצאו (סה\"כ {len(saved['stocks'])}):")
            st.write(', '.join(saved['stocks']))
            
            # אם תרצה, אפשר להוסיף כאן אפשרות לבחור מניה מהרשימה השמורה ולהציג את הגרף שלה
    else:
        st.info("טרם בוצעה סריקת רשימה לשמירה.")
