import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="מערכת וייקוף Pro", layout="wide")
st.title("◈ מערכת השקעות מבוססת וייקוף")

PORTFOLIO_FILE = 'portfolio.csv'

# הוספנו קישור ל-AI!
ANALYSIS_SITES = {
    "Yahoo Finance": "https://finance.yahoo.com/quote/",
    "Finviz": "https://finviz.com/quote.ashx?t=",
    "Investing.com": "https://www.investing.com/search/?q=",
    "Webull": "https://www.webull.com/quote/",
    "AI Wyckoff Analyst": "https://chatgpt.com/?q=Analyze+stock+ticker+" 
}

# --- פונקציות עזר ---
@st.cache_data
def load_selected_list(filename):
    df = pd.read_csv(filename)
    return df['Ticker'].dropna().astype(str).tolist()

def calculate_wyckoff_score(df):
    if df is None or len(df) < 20: return 0, 0, 0
    recent = df.tail(20)
    up = recent[recent['Close'] >= recent['Close'].shift(1)]
    down = recent[recent['Close'] < recent['Close'].shift(1)]
    vr = (up['Volume'].mean() / down['Volume'].mean()) if down['Volume'].mean() > 0 else 1
    rw = (recent['High'].max() - recent['Low'].min()) / ((recent['High'].max() + recent['Low'].min()) / 2) * 100
    score = min((40 if vr > 1.2 else 0) + (40 if rw < 7 else 0) + (20 if rw < 4 else 0), 100)
    return score, vr, rw

def get_portfolio_df():
    if not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0:
        return pd.DataFrame(columns=['Ticker', 'Date', 'EntryPrice'])
    return pd.read_csv(PORTFOLIO_FILE)

def display_analysis_selector(ticker):
    col1, col2 = st.columns([1, 2])
    with col1:
        site_name = st.selectbox("בחר פלטפורמת ניתוח:", list(ANALYSIS_SITES.keys()), key=f"site_{ticker}")
    with col2:
        st.write("---") 
        # הקישור ל-AI עובד עכשיו בדיוק כמו יאהו
        url = f"{ANALYSIS_SITES[site_name]}{ticker}"
        if "chatgpt" in url:
            url += "+using+Wyckoff+Strategy"
        st.link_button(f"עבור ל-{site_name}", url)

# --- ממשק ---
tab1, tab2, tab3 = st.tabs(["📊 סורק וייקוף", "💼 תיק השקעות", "💡 אסטרטגיית וייקוף"])

with tab1:
    file_options = [f"nasdaq_{i}.csv" for i in range(1, 28)]
    selected_file = st.sidebar.selectbox("בחר רשימת סריקה:", file_options)
    min_score = st.sidebar.slider("ציון מינימלי:", 0, 100, 40)

    if st.sidebar.button("הרץ סריקה"):
        try:
            tickers = load_selected_list(selected_file)
            results = []
            with st.spinner(f"סורק את {selected_file}..."):
                for ticker in tickers:
                    try:
                        df = yf.Ticker(ticker).history(period="3mo")
                        if not df.empty and df['Close'].iloc[-1] >= 5:
                            score, vr, rw = calculate_wyckoff_score(df)
                            results.append({
                                "Ticker": ticker, 
                                "Score": score, 
                                "Price": round(df['Close'].iloc[-1], 2),
                                "VR (Volume Ratio)": round(vr, 2),
                                "RW (Range Width)": round(rw, 2)
                            })
                    except Exception: continue
            st.session_state['results_df'] = pd.DataFrame(results)
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בטעינת הקובץ: {e}")

    if st.session_state.get('results_df') is not None:
        filtered_df = st.session_state['results_df'][st.session_state['results_df']['Score'] >= min_score].sort_values("Score", ascending=False)
        st.dataframe(filtered_df, use_container_width=True)
        
        st.divider()
        if not filtered_df.empty:
            to_add = st.selectbox("בחר מניה להוספה לתיק:", filtered_df['Ticker'].tolist())
            if st.button("הוסף לתיק ההשקעות 💼"):
                price = filtered_df[filtered_df['Ticker'] == to_add]['Price'].values[0]
                new_row = pd.DataFrame({'Ticker': [to_add], 'Date': [datetime.now().strftime('%Y-%m-%d')], 'EntryPrice': [price]})
                new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE), index=False)
                st.success(f"{to_add} נוספה בהצלחה!")

with tab2:
    portfolio = get_portfolio_df()
    if not portfolio.empty:
        portfolio['CurrentPrice'] = 0.0
        portfolio['Performance'] = "0%"
        for i, row in portfolio.iterrows():
            try:
                curr = yf.Ticker(row['Ticker']).history(period="1d")['Close'].iloc[-1]
                portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
                portfolio.loc[i, 'Performance'] = f"{round(((curr - row['EntryPrice']) / row['EntryPrice']) * 100, 2)}%"
            except Exception:
                portfolio.loc[i, 'CurrentPrice'] = 0.0
                portfolio.loc[i, 'Performance'] = "N/A"
        
        st.dataframe(portfolio, use_container_width=True)
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].unique().tolist())
        display_analysis_selector(to_manage)
        
        if st.button("מחק מניה מהתיק 🗑️"):
            portfolio = portfolio[portfolio['Ticker'] != to_manage]
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()
    else:
        st.info("התיק ריק כרגע.")

with tab3:
    st.markdown("<h2 style='color:green;'>אסטרטגיית וייקוף (Wyckoff Strategy)</h2>", unsafe_allow_html=True)
    st.write("---")
    st.success("""
    **עקרונות המפתח של השיטה:**
    1. **חוק ההיצע והביקוש:** כאשר הביקוש עולה על ההיצע, המחיר עולה. הסורק שלנו מזהה זאת דרך ה-**Volume Ratio (VR)**.
    2. **שלבי שוק:**
       - **Accumulation (איסוף):** כסף חכם קונה בשקט בטווח מחירים צר. כאן ה-**Range Width (RW)** שלנו נמוך.
       - **Markup (עליית ערך):** המניה פורצת את הדשדוש בלוויית ווליום גבוה.
    
    **איך להשתמש בסורק:**
    - חפש מניות עם ציון גבוה (Score > 70).
    - וודא שה-VR גבוה מ1.2 (סימן לעניין מצד המוסדיים).
    - השתמש בגרפים חיצוניים (Yahoo/Finviz) כדי לוודא פריצה של קווי התנגדות.
    """)
    st.info("זכור: שום אסטרטגיה אינה מבטיחה רווח. נהל סיכונים בהתאם!")
