# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
import traceback
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף — סורק פריצה משופר")

PORTFOLIO_FILE = 'portfolio.csv'
SCAN_RESULTS_FILE = 'scan_results.csv'  # קובץ לשמירת תוצאות הסריקה

# ============================
# פונקציות עזר בטוחות
# ============================

def safe_last(s):
    """מחזיר ערך יחיד מהסדרה או np.nan אם אין ערך"""
    try:
        if s is None:
            return np.nan
        if hasattr(s, "iloc"):
            if len(s) == 0:
                return np.nan
            return s.iloc[-1]
        return s
    except Exception:
        return np.nan

def validate_df(df, required_cols=None):
    """בודק אם df תקין ואם קיימות העמודות הנדרשות"""
    if df is None or df.empty:
        return False, "DataFrame ריק"
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return False, f"עמודות חסרות: {missing}"
    return True, None

# ============================
# טעינת טיקרים מקבצי CSV / תיקיה
# ============================

def get_csv_files_in_cwd():
    """מחזיר רשימת כל קבצי ה-CSV בתיקייה הנוכחית"""
    return [f for f in os.listdir('.') if f.lower().endswith('.csv')]

def tickers_from_csv_file(path):
    """מנסה לקרוא עמודת Ticker/Symbol; אם לא קיימת מחזיר שם הקובץ"""
    try:
        df = pd.read_csv(path)
        cols = [c.strip().lower() for c in df.columns]

        if 'ticker' in cols:
            col = [c for c in df.columns if c.strip().lower() == 'ticker'][0]
            return df[col].dropna().astype(str).str.upper().tolist()

        if 'symbol' in cols:
            col = [c for c in df.columns if c.strip().lower() == 'symbol'][0]
            return df[col].dropna().astype(str).str.upper().tolist()

    except Exception:
        pass

    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    return [name.upper()]

def load_tickers_from_folder(folder_path):
    """טוען את כל הטיקרים מכל קבצי ה-CSV בתיקיה (לא רק קובץ אחד)"""
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    all_tickers = []

    for f in csv_files:
        try:
            tickers = tickers_from_csv_file(f)
            all_tickers.extend(tickers)
        except Exception as e:
            st.warning(f"בעיה בקריאת {f}: {e}")

    seen = set()
    unique = []
    for t in all_tickers:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique

# ============================
# הורדת נתונים והוספת אינדיקטורים
# ============================

@st.cache_data
def load_history(ticker, period="6mo"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        df.dropna(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def add_indicators(df):
    df = df.copy()
    if df.empty:
        return df

    # EMAs
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # ATR
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # Volatility and MA
    df["STD20"] = df["Close"].rolling(20).std()
    df["MA20"] = df["Close"].rolling(20).mean()

    # Bollinger and Keltner
    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]
    df["UpperKC"] = df["MA20"] + df["ATR"] * 1.5
    df["LowerKC"] = df["MA20"] - df["ATR"] * 1.5

    # OBV and AD
    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    ad = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"]).replace(0,1) * df["Volume"]
    df["AD_Cum"] = ad.cumsum()

    # MFI
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical * df["Volume"]
    pos_flow = money_flow.where(typical > typical.shift(1), 0).rolling(14).sum()
    neg_flow = money_flow.where(typical < typical.shift(1), 0).rolling(14).sum()
    df["MFI"] = 100 - (100 / (1 + (pos_flow / neg_flow.replace(0,1))))

    # RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0,1)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # Volume MA and RVOL
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    df["RVOL"] = df["Volume"] / df["VOL_MA20"]

    return df

# ============================
# מנוע החלטה לפני פריצה
# ============================

def score_component(value, low, high, invert=False):
    """ממפה ערך ל-0..100 לפי טווח; invert הופך את הכיוון"""
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return 0
        if low == high:
            return 100 if not invert else 0
        v = (value - low) / (high - low)
        v = max(0.0, min(1.0, v))
        if invert:
            v = 1.0 - v
        return int(round(v * 100))
    except Exception:
        return 0

def compute_breakout_decision(df):
    """מחזיר dict עם score, confidence, risk, components, note"""
    ok, msg = validate_df(df, ["High","Low","Close","Volume","EMA20","EMA50","ATR","STD20","OBV","AD_Cum","MACD","Signal","RSI","MA20","UpperBB","LowerBB","UpperKC","LowerKC","VOL_MA20"])
    if not ok:
        return {"score":0, "confidence":0, "risk":100, "components":{}, "note":"נתונים חסרים"}

    comps = {}

    # 1. Volatility compression (lower STD20 is better)
    std20 = safe_last(df["STD20"])
    hist_std = df["STD20"].dropna()
    if len(hist_std) >= 30:
        low_std, high_std = hist_std.quantile(0.05), hist_std.quantile(0.95)
    else:
        low_std, high_std = (hist_std.min() if not hist_std.empty else 0), (hist_std.max() if not hist_std.empty else 1)
    comps["compression"] = score_component(std20, low_std, high_std, invert=True)

    # 2. RVOL (relative volume)
    vol_ma20 = safe_last(df["VOL_MA20"])
    rvol = safe_last(df["Volume"]) / vol_ma20 if vol_ma20 not in [0, None, np.nan] else 1
    comps["rvol"] = score_component(rvol, 0.5, 3.0)

    # 3. Trend (EMA20 / EMA50)
    ema20, ema50 = safe_last(df["EMA20"]), safe_last(df["EMA50"])
    trend_ratio = ema20 / ema50 if ema50 not in [0, None, np.nan] else 1
    comps["trend"] = score_component(trend_ratio, 0.95, 1.1)

    # 4. Momentum (MACD diff and RSI)
    macd_diff = safe_last(df["MACD"]) - safe_last(df["Signal"])
    comps["macd"] = score_component(macd_diff, -1.0, 2.0)
    comps["rsi"] = score_component(safe_last(df["RSI"]), 40, 70)

    # 5. Institutional flow (OBV and AD)
    obv_gain = 1 if (safe_last(df["OBV"]) > safe_last(df["OBV"].shift(10))) else 0
    ad_gain = 1 if (safe_last(df["AD_Cum"]) > safe_last(df["AD_Cum"].shift(10))) else 0
    comps["institutional"] = int(round(((obv_gain + ad_gain) / 2) * 100))

    # 6. Proximity to breakout (close to 20-day high)
    high20 = df["High"].rolling(20).max()
    prox = safe_last(df["Close"]) / safe_last(high20) if safe_last(high20) not in [0, None, np.nan] else 0
    comps["proximity"] = score_component(prox, 0.9, 1.02)

    # 7. Risk (ATR as percent of price) — lower is better
    atr_pct = safe_last(df["ATR"]) / safe_last(df["Close"]) if safe_last(df["Close"]) not in [0, None, np.nan] else 0
    comps["risk"] = score_component(atr_pct, 0.0, 0.06, invert=True)

    # 8. Squeeze (BB inside KC)
    sq = (
        safe_last(df["UpperBB"]) < safe_last(df["UpperKC"]) and
        safe_last(df["LowerBB"]) > safe_last(df["LowerKC"])
    )
    comps["squeeze"] = 100 if sq else 0

    # Weights for final score
    weights = {
        "compression": 0.20,
        "rvol": 0.20,
        "trend": 0.15,
        "macd": 0.10,
        "rsi": 0.05,
        "institutional": 0.10,
        "proximity": 0.10,
        "squeeze": 0.05,
        "risk": 0.05
    }

    final_score = sum(comps.get(k, 0) * w for k, w in weights.items())
    final_score = int(round(final_score))

    # Confidence: כמה רכיבים חזקים
    strong = sum(1 for v in comps.values() if v >= 70)
    confidence = int(round((strong / len(comps)) * 100)) if len(comps) > 0 else 0

    # Risk metric (higher = more risky)
    risk_metric = 100 - comps.get("risk", 0)

    # Notes
    notes = []
    if comps.get("compression", 0) >= 70: notes.append("דחיסה חזקה")
    if comps.get("rvol", 0) >= 70: notes.append("נפח תומך")
    if comps.get("trend", 0) >= 70: notes.append("טרנד עולה")
    if comps.get("institutional", 0) >= 60: notes.append("כסף מוסדי נכנס")
    if comps.get("squeeze", 0) == 100: notes.append("Squeeze פעיל")
    if prox < 0.95: notes.append("עדיין רחוק מהפריצה")
    note = ", ".join(notes) if notes else "אין אותות חזקים"

    return {
        "score": final_score,
        "confidence": confidence,
        "risk": risk_metric,
        "components": comps,
        "note": note
    }

# ============================
# שמירת תוצאות סריקה ופעולות מחיקה
# ============================

def save_scan_results(df_results):
    """שומר DataFrame של תוצאות סריקה לקובץ CSV (מוסיף אם קיים)"""
    if df_results is None or df_results.empty:
        return False
    header = not os.path.exists(SCAN_RESULTS_FILE)
    df_results.to_csv(SCAN_RESULTS_FILE, mode='a', header=header, index=False)
    return True

def load_saved_results():
    """טוען תוצאות סריקה שמורות"""
    if not os.path.exists(SCAN_RESULTS_FILE):
        return pd.DataFrame(columns=["Ticker","Score","Confidence","Risk","Price","Note","SavedAt"])
    try:
        df = pd.read_csv(SCAN_RESULTS_FILE)
        return df
    except Exception:
        return pd.DataFrame(columns=["Ticker","Score","Confidence","Risk","Price","Note","SavedAt"])

def delete_saved_tickers(tickers_to_delete):
    """מוחק רשומות של טיקרים מתוך קובץ התוצאות השמורות"""
    if not os.path.exists(SCAN_RESULTS_FILE):
        return False
    try:
        df = pd.read_csv(SCAN_RESULTS_FILE)
        df = df[~df['Ticker'].isin(tickers_to_delete)]
        df.to_csv(SCAN_RESULTS_FILE, index=False)
        return True
    except Exception:
        return False

def clear_saved_results():
    """מוחק את כל קובץ התוצאות השמורות"""
    if os.path.exists(SCAN_RESULTS_FILE):
        try:
            os.remove(SCAN_RESULTS_FILE)
            return True
        except Exception:
            return False
    return True

# ============================
# גרף מפורט
# ============================

def plot_advanced(df, ticker):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        row_heights=[0.5, 0.12, 0.18, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    if "MA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], line=dict(color="blue"), name="MA20"), row=1, col=1)
    if "UpperBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="lightblue"), name="UpperBB"), row=1, col=1)
    if "LowerBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="lightblue"), name="LowerBB"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)
    if "OBV" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV"), row=3, col=1)
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"), row=4, col=1)
    if "Signal" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal"), row=4, col=1)
    fig.update_layout(height=900, title=f"{ticker} — Decision Chart")
    return fig

# ============================
# תיק השקעות
# ============================

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df
    try:
        return pd.read_csv(PORTFOLIO_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
        df.to_csv(PORTFOLIO_FILE, index=False)
        return df

def show_buttons(ticker):
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"[Yahoo](https://finance.yahoo.com/quote/{ticker})")
    with c2: st.markdown(f"[Finviz](https://finviz.com/quote.ashx?t={ticker})")
    c3, c4 = st.columns(2)
    with c3: st.markdown(f"[Investing](https://www.investing.com/search/?q={ticker})")
    with c4: st.markdown(f"[Webull](https://www.webull.com/quote/{ticker})")

# ============================
# ממשק משתמש — טאבים
# ============================

tab1, tab2, tab3 = st.tabs(["📊 סורק פריצה משופר", "💼 תיק השקעות", "💾 תוצאות שמורות"])

# --- טאב הסורק ---
with tab1:
    st.sidebar.header("מקורות טיקרים לסורק")
    mode = st.sidebar.radio(
        "בחר מקור:",
        ["קובץ CSV בודד", "תיקיית CSV", "רשימת CSV בתיקייה הנוכחית", "הקלדה ידנית"]
    )

    tickers = []

    if mode == "קובץ CSV בודד":
        uploaded = st.sidebar.file_uploader("העלה קובץ CSV עם עמודת Ticker או Symbol", type=["csv"])
        if uploaded:
            try:
                dfu = pd.read_csv(uploaded)
                cols = [c.strip().lower() for c in dfu.columns]
                if 'ticker' in cols:
                    col = [c for c in dfu.columns if c.strip().lower() == 'ticker'][0]
                    tickers = dfu[col].dropna().astype(str).str.upper().tolist()
                elif 'symbol' in cols:
                    col = [c for c in dfu.columns if c.strip().lower() == 'symbol'][0]
                    tickers = dfu[col].dropna().astype(str).str.upper().tolist()
                else:
                    st.sidebar.error("לא נמצאה עמודת Ticker/Symbol בקובץ")
            except Exception as e:
                st.sidebar.error(f"שגיאה בקריאת הקובץ: {e}")

    elif mode == "תיקיית CSV":
        folder = st.sidebar.text_input("נתיב לתיקיה:", ".")
        if folder and os.path.isdir(folder):
            tickers = load_tickers_from_folder(folder)
            st.sidebar.success(f"נטענו {len(tickers)} טיקרים מהתיקיה")
        elif folder:
            st.sidebar.error("התיקיה לא קיימת")

    elif mode == "רשימת CSV בתיקייה הנוכחית":
        available_lists = get_csv_files_in_cwd()
        if available_lists:
            selected_file = st.sidebar.selectbox("בחר קובץ מהרשימה:", available_lists)
            tickers = tickers_from_csv_file(selected_file)
            st.sidebar.success(f"נטענו {len(tickers)} טיקרים מהקובץ")
        else:
            st.sidebar.info("אין קבצי CSV בתיקייה הנוכחית")

    else:  # הקלדה ידנית
        txt = st.sidebar.text_area("טיקרים (מופרדים בפסיק):", "AAPL, MSFT, NVDA")
        tickers = [t.strip().upper() for t in txt.split(",") if t.strip()]

    min_score = st.sidebar.slider("ציון מינימלי להצגה:", 0, 100, 60)
    max_tickers = st.sidebar.number_input("מקסימום טיקרים לסריקה:", min_value=10, max_value=1000, value=200, step=10)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**הערה**: כלי תמיכה בהחלטה בלבד, לא ייעוץ השקעות.")

    if st.sidebar.button("הרץ סריקת פריצה"):
        if not tickers:
            st.error("לא נבחרו טיקרים")
        else:
            tickers = tickers[:int(max_tickers)]
            results = []
            details = {}
            progress = st.progress(0)
            total = len(tickers)

            for i, ticker in enumerate(tickers):
                try:
                    st.write(f"בודק {ticker} ({i+1}/{total})")
                    df = load_history(ticker, period="6mo")
                    if df.empty:
                        results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100, "Price": np.nan, "Note": "אין נתונים", "SavedAt": ""})
                        progress.progress((i+1)/total)
                        continue
                    df = add_indicators(df)
                    res = compute_breakout_decision(df)
                    results.append({
                        "Ticker": ticker,
                        "Score": res["score"],
                        "Confidence": res["confidence"],
                        "Risk": res["risk"],
                        "Price": round(float(safe_last(df["Close"])), 2) if not np.isnan(safe_last(df["Close"])) else np.nan,
                        "Note": res["note"],
                        "SavedAt": ""
                    })
                    details[ticker] = {"res": res, "df_tail": df.tail(60)}
                except Exception as e:
                    results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100, "Price": np.nan, "Note": "שגיאה", "SavedAt": ""})
                progress.progress((i+1)/total)

            df_res = pd.DataFrame(results).sort_values("Score", ascending=False).reset_index(drop=True)
            df_res = df_res[df_res["Score"] >= min_score]

            if df_res.empty:
                st.info("לא נמצאו מניות מתאימות לפי הקריטריונים.")
            else:
                st.subheader("תוצאות סריקה")
                st.dataframe(df_res, use_container_width=True)

                # שמירת תוצאות: כפתור ושדה שם קובץ אופציונלי
                st.divider()
                col_save1, col_save2 = st.columns([3,1])
                with col_save1:
                    save_note = st.text_input("הערה לשמירה (אופציונלי):", "")
                with col_save2:
                    if st.button("שמור תוצאות"):
                        # הוספת עמודת SavedAt ושמירת תוצאות
                        df_to_save = df_res.copy()
                        df_to_save["SavedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if save_note:
                            df_to_save["Note"] = df_to_save["Note"].astype(str) + " | " + save_note
                        saved = save_scan_results(df_to_save)
                        if saved:
                            st.success("תוצאות נשמרו בהצלחה")
                        else:
                            st.error("שגיאה בשמירת התוצאות")

                st.divider()
                col_select, col_buttons = st.columns([2, 1])
                with col_select:
                    to_view = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].tolist())
                with col_buttons:
                    if st.button("הוסף לתיק ההשקעות 💼"):
                        try:
                            price = df_res[df_res['Ticker'] == to_view]['Price'].values[0]
                        except Exception:
                            price = None
                        new_row = pd.DataFrame({'Ticker': [to_view], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
                        new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                        st.success(f"{to_view} נוספה בהצלחה לתיק!")

                # דוח מפורט לטיקר הנבחר
                st.subheader("דוח מפורט לטיקר")
                sel = to_view
                info = details.get(sel)
                if info:
                    res = info["res"]
                    st.metric("ציון פריצה", res["score"])
                    st.metric("ביטחון", res["confidence"])
                    st.metric("מדד סיכון", res["risk"])
                    st.write("**רכיבי ניקוד**")
                    comp_df = pd.DataFrame.from_dict(res["components"], orient="index", columns=["Value"]).sort_values("Value", ascending=False)
                    st.table(comp_df)
                    st.write("**הערות**")
                    st.info(res["note"])

                    df_plot = info["df_tail"].copy()
                    st.plotly_chart(plot_advanced(df_plot, sel), use_container_width=True)

                    show_buttons(sel)
                else:
                    st.warning("אין פרטים לטיקר זה")

                # הורדה של התוצאות
                csv_data = df_res.to_csv(index=False).encode('utf-8')
                st.download_button("הורד תוצאות כ־CSV", csv_data, file_name="decision_scan_results.csv", mime="text/csv")

# --- טאב תיק ההשקעות ---
with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        for i, row in portfolio.iterrows():
            try:
                curr = yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1]
                portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
                portfolio.loc[i, 'Performance'] = f"{round(((curr - row['EntryPrice']) / row['EntryPrice']) * 100, 2)}%"
            except Exception:
                portfolio.loc[i, 'CurrentPrice'] = np.nan
                portfolio.loc[i, 'Performance'] = "N/A"

        st.dataframe(portfolio, use_container_width=True)

        st.divider()
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())

        show_buttons(to_manage)

        if st.button("מחק מניה מהתיק 🗑️"):
            portfolio = portfolio[portfolio['Ticker'] != to_manage]
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{to_manage} הוסר מהתיק")
            st.experimental_rerun()
    else:
        st.info("התיק ריק.")

# --- טאב תוצאות שמורות ---
with tab3:
    st.header("תוצאות סריקה שמורות")
    saved = load_saved_results()
    if saved.empty:
        st.info("אין תוצאות שמורות כרגע.")
    else:
        st.dataframe(saved, use_container_width=True)

        st.divider()
        col_del1, col_del2 = st.columns([3,1])
        with col_del1:
            to_delete = st.multiselect("בחר טיקרים למחיקה מהתוצאות השמורות:", options=sorted(saved['Ticker'].unique().tolist()))
        with col_del2:
            if st.button("מחק נבחרים"):
                if not to_delete:
                    st.warning("לא נבחרו טיקרים למחיקה")
                else:
                    ok = delete_saved_tickers(to_delete)
                    if ok:
                        st.success("הפריטים נמחקו מהקובץ השמור")
                        st.experimental_rerun()
                    else:
                        st.error("שגיאה במחיקה")

        st.divider()
        if st.button("נקה את כל התוצאות השמורות"):
            ok = clear_saved_results()
            if ok:
                st.success("כל התוצאות השמורות נמחקו")
                st.experimental_rerun()
            else:
                st.error("שגיאה בניקוי הקובץ השמור")

        # אפשרות להוריד את כל התוצאות השמורות כקובץ CSV
        csv_all = saved.to_csv(index=False).encode('utf-8')
        st.download_button("הורד את כל התוצאות השמורות כ־CSV", csv_all, file_name="saved_scan_results.csv", mime="text/csv")
