import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile

# ---------- הגדרות ----------
st.set_page_config(page_title="KEISAR Pro Hunter", layout="wide")
PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'
MAX_WORKERS = 5  # להגבלת בקשות מקבילות ל-yfinance

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ---------- פונקציות עזר ----------
def atomic_write_csv(df: pd.DataFrame, path: str, mode: str = 'w', header: bool = True):
    """כתיבה אטומית לקובץ CSV (מונע קבצים חלקיים)"""
    dirn = os.path.dirname(os.path.abspath(path)) or '.'
    with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=dirn, suffix='.tmp') as tmp:
        df.to_csv(tmp.name, index=False, header=header)
        tmp_name = tmp.name
    os.replace(tmp_name, path)

def read_ticker_file(path):
    """קריאת קובץ טיקרים בצורה בטוחה והחזרת רשימה של טיקרים תקינים"""
    try:
        s = pd.read_csv(path, header=None).iloc[:, 0].dropna().astype(str).str.strip().str.upper().unique().tolist()
        return [t for t in s if t]
    except Exception as e:
        logging.error(f"Error reading {path}: {e}")
        return []

# ---------- קבלת נתונים עם cache ברמת session ----------
@st.cache_data(ttl=3600)
def fetch_history(ticker):
    """קריאה ל-yfinance; מטמון גלובלי של Streamlit לפי ticker"""
    return yf.Ticker(ticker).history(period="6mo")

def get_data_cached(ticker):
    """מעט עטיפה כדי להחזיר None במקרה של שגיאה"""
    try:
        df = fetch_history(ticker)
        if df is None or df.empty:
            raise ValueError("No data")
        return df
    except Exception as e:
        logging.warning(f"fetch_history failed for {ticker}: {e}")
        return None

# ---------- אינדיקטורים ----------
def get_indicators(df):
    df = df.copy()
    df['Daily_Change'] = df['Close'].pct_change()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['Close']
    # OBV סטנדרטי
    direction = np.sign(df['Close'].diff()).fillna(0)
    df['OBV'] = (df['Volume'] * direction).cumsum()
    df['AvgVol'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['AvgVol']
    high_low = df['High'] - df['Low']
    df['ATR'] = high_low.rolling(window=14).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

def calculate_score(df):
    try:
        if df['Daily_Change'].iloc[-1] < -0.05:
            return -1
        score = 0
        if df['Squeeze'].iloc[-1] < 0.10:
            score += 2
        elif df['Squeeze'].iloc[-1] < 0.15:
            score += 1
        if df['Close'].iloc[-1] > df['MA20'].iloc[-1]:
            score += 1
        if df['OBV'].iloc[-1] > df['OBV'].iloc[-10]:
            score += 1
        if df['RVOL'].iloc[-1] > 1.5:
            score += 1
        return score
    except Exception as e:
        logging.warning(f"calculate_score error: {e}")
        return 0

def get_market_status():
    try:
        spy = yf.Ticker("SPY").history(period="1y")
        spy['MA200'] = spy['Close'].rolling(window=200).mean()
        return spy['Close'].iloc[-1] > spy['MA200'].iloc[-1]
    except Exception as e:
        logging.warning(f"get_market_status failed: {e}")
        return True  # אם נכשל, לא לחסום את המשתמש

# ---------- ממשק משתמש ----------
st.title("◈ KEISAR: סורק מוסדי מקצועי")

if not get_market_status():
    st.warning("⚠️ אזהרת מערכת: השוק (SPY) מתחת ל-MA200.")

tab1, tab2, tab3 = st.tabs(["📊 סורק", "💼 תיק השקעות", "🎓 מדריך אסטרטגי"])

with tab1:
    st.sidebar.header("⚙️ הגדרות סריקה")
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'portfolio' not in f and 'scan_results' not in f]
    selected_files = st.sidebar.multiselect("בחר קבצי רשימות:", all_files, default=all_files)

    run_scan = st.button("🚀 הפעל סריקה")
    if run_scan:
        # בניית רשימת טיקרים
        all_tickers = []
        for file in selected_files:
            all_tickers.extend(read_ticker_file(file))
        all_tickers = list(dict.fromkeys(all_tickers))  # שמירה על סדר והסרת כפילויות

        if not all_tickers:
            st.info("לא נמצאו טיקרים בקבצים שנבחרו.")
        else:
            progress_bar = st.progress(0)
            master_list = []
            alerts = []
            futures = []
            # שימוש ב-ThreadPoolExecutor לקריאות מקבילות מבוקרות
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for ticker in all_tickers:
                    futures.append(executor.submit(get_data_cached, ticker))

                for i, future in enumerate(as_completed(futures)):
                    try:
                        df_hist = future.result()
                        # צריך לדעת איזה טיקר שייך לתוצאה; פשוט נבדוק לפי סדר all_tickers
                        # כדי לשמור התאמה מדויקת, נשתמש בגישה פשוטה: בקשות נשלחות לפי סדר, לכן נשתמש באינדקס i
                        # הערה: as_completed משנה סדר ההשלמה; לכן במקום זאת נבצע mapping של futures->tickers
                    except Exception as e:
                        logging.warning(f"Future error: {e}")

            # חלופה: מפה מפורשת של futures->tickers
            progress_bar.progress(0)
            master_list = []
            alerts = []
            future_to_ticker = {}
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for ticker in all_tickers:
                    future = executor.submit(get_data_cached, ticker)
                    future_to_ticker[future] = ticker

                total = len(all_tickers)
                done = 0
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    done += 1
                    try:
                        df_hist = future.result()
                        if df_hist is None:
                            logging.info(f"No data for {ticker}")
                            progress_bar.progress(done / total)
                            continue
                        df = get_indicators(df_hist)
                        if len(df) > 50:
                            score = calculate_score(df)
                            if score >= 0:
                                master_list.append({
                                    "Ticker": ticker,
                                    "Score": score,
                                    "Price": round(float(df['Close'].iloc[-1]), 2),
                                    "RVOL": round(float(df['RVOL'].iloc[-1]), 2)
                                })
                                if score >= 4 and df['RVOL'].iloc[-1] > 1.5:
                                    alerts.append(f"🔥 איתות חם: {ticker} בציון {score} ו-RVOL {round(float(df['RVOL'].iloc[-1]), 2)}!")
                    except Exception as e:
                        logging.warning(f"Failed processing {ticker}: {e}")
                    progress_bar.progress(done / total)

            # שמירת תוצאות סריקה אטומית
            if master_list:
                df_out = pd.DataFrame(master_list).sort_values(by="Score", ascending=False)
                try:
                    atomic_write_csv(df_out, SCAN_RESULTS_FILE, header=True)
                except Exception as e:
                    logging.error(f"Failed to write scan results: {e}")
            else:
                # מחיקת קובץ תוצאות אם אין תוצאות
                if os.path.exists(SCAN_RESULTS_FILE):
                    try:
                        os.remove(SCAN_RESULTS_FILE)
                    except Exception:
                        pass

            st.session_state['alerts'] = alerts
            st.success("סריקה הושלמה.")

    # הצגת התראות אם קיימות
    if 'alerts' in st.session_state and st.session_state['alerts']:
        st.error("🚨 מרכז התראות בזמן אמת:")
        for alert in st.session_state['alerts']:
            st.write(alert)

    # הצגת תוצאות סריקה
    if os.path.exists(SCAN_RESULTS_FILE):
        try:
            df_res = pd.read_csv(SCAN_RESULTS_FILE)
            if not df_res.empty:
                selected = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].unique())
                if st.button("הצג ניתוח"):
                    st.session_state['selected_ticker'] = selected

                if 'selected_ticker' in st.session_state:
                    ticker = st.session_state['selected_ticker']
                    data_hist = get_data_cached(ticker)
                    if data_hist is None:
                        st.warning("לא ניתן לקבל נתונים עבור המניה שנבחרה.")
                    else:
                        data = get_indicators(data_hist)
                        last_price = float(data['Close'].iloc[-1])
                        atr = float(data['ATR'].iloc[-1])
                        sl = round(last_price - (1.5 * atr), 2)
                        tp = round(last_price + (3.0 * atr), 2)
                        risk = last_price - sl
                        reward = tp - last_price
                        rr_ratio = round(reward / risk, 2) if risk != 0 else float('inf')

                        st.subheader(f"📊 ניתוח טכני: {ticker}")
                        st.markdown("""
                        <div style="display: flex; justify-content: space-between; align-items: center; background-color: #f8f9fa; padding: 15px; border-radius: 10px;">
                            <div style="text-align: center;"><b>מחיר</b><br>${:.2f}</div>
                            <div style="text-align: center; color: red;"><b>SL</b><br>${:.2f}</div>
                            <div style="text-align: center; color: green;"><b>TP</b><br>${:.2f}</div>
                            <div style="text-align: center;"><b>R/R</b><br>1 : {:.2f}</div>
                        </div>
                        """.format(last_price, sl, tp, rr_ratio), unsafe_allow_html=True)

                        st.markdown("---")
                        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
                        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=data.index, y=data['RVOL'], name='RVOL', line=dict(color='orange')), row=2, col=1)
                        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD'), row=3, col=1)
                        fig.update_layout(height=600, margin=dict(l=20, r=20, t=30, b=20))
                        st.plotly_chart(fig, use_container_width=True)

                        if st.button("הוסף לתיק"):
                            new_entry = pd.DataFrame({
                                'Ticker': [ticker],
                                'Entry': [last_price],
                                'SL': [sl],
                                'TP': [tp],
                                'Date': [datetime.now().strftime("%Y-%m-%d")]
                            })
                            try:
                                if os.path.exists(PORTFOLIO_FILE):
                                    df_port = pd.read_csv(PORTFOLIO_FILE)
                                    df_port = pd.concat([df_port, new_entry], ignore_index=True)
                                else:
                                    df_port = new_entry
                                atomic_write_csv(df_port, PORTFOLIO_FILE, header=True)
                                st.success(f"{ticker} נוספה לתיק!")
                            except Exception as e:
                                logging.error(f"Failed to add to portfolio: {e}")
                                st.error("שגיאה בשמירת התיק.")
            else:
                st.info("אין תוצאות בסריקה.")
        except Exception as e:
            logging.error(f"Error reading scan results: {e}")
            st.error("שגיאה בקריאת תוצאות הסריקה.")

with tab2:
    st.subheader("💼 התיק הפעיל שלך")
    if os.path.exists(PORTFOLIO_FILE):
        try:
            df_port = pd.read_csv(PORTFOLIO_FILE)
            if df_port.empty:
                st.info("התיק עדיין ריק.")
            else:
                for i, row in df_port.iterrows():
                    col1, col2 = st.columns([0.8, 0.2])
                    data_hist = get_data_cached(row['Ticker'])
                    if data_hist is None:
                        curr_p = float('nan')
                        ret = float('nan')
                    else:
                        curr_p = float(data_hist['Close'].iloc[-1])
                        ret = ((curr_p - float(row['Entry'])) / float(row['Entry'])) * 100

                    col1.write(f"**{row['Ticker']}** | כניסה: ${float(row['Entry']):.2f} | **נוכחי: ${curr_p:.2f}** | תשואה: {ret:.2f}%")
                    col1.caption(f"יעדים: SL ${row['SL']} | TP ${row['TP']}")

                    if col2.button("🗑️ הסר", key=f"del_{i}"):
                        df_port = df_port.drop(i).reset_index(drop=True)
                        try:
                            atomic_write_csv(df_port, PORTFOLIO_FILE, header=True)
                            st.experimental_rerun()
                        except Exception as e:
                            logging.error(f"Failed to remove from portfolio: {e}")
                            st.error("שגיאה בהסרת הפריט.")
        except Exception as e:
            logging.error(f"Error reading portfolio: {e}")
            st.error("שגיאה בקריאת התיק.")
    else:
        st.info("התיק עדיין ריק.")

with tab3:
    st.header("🎓 מדריך אסטרטגי: צייד התפרצויות (ASST)")
    st.markdown("""
    ### ניהול סיכונים חכם
    * **R/R Ratio:** יחס הסיכוי מול הסיכון. שאיפה ל-1.5 ומעלה.
    * **ATR:** כלי התנודתיות שקובע היכן הסטופ שלך צריך להיות.
    """)
    st.info("הערה: המידע המוצג הוא לצורכי לימוד בלבד ואינו מהווה ייעוץ פיננסי.")
