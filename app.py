import streamlit as st
import yfinance as yf
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide", page_title="TITAN: Pro Scanner")

# --- טעינת יקום מניות ---
@st.cache_data(ttl=86400)
def get_universe():
    url = "https://raw.githubusercontent.com/liorkeisar/Momentum-stock-scanner/main/nasdaq_screener.csv"
    try:
        df = pd.read_csv(url)
        return [str(t) for t in df['Symbol'].dropna().unique().tolist() if len(str(t)) < 6 and str(t).isalpha()]
    except: return ["AAPL", "NVDA", "MSFT"]

# --- מנוע סריקה ---
def run_scanner(ticker, mode):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="300d")
        if len(df) < 252 or df['Volume'].rolling(20).mean().iloc[-1] < 500000: return None
        
        info = stock.info
        sector = info.get('sector', 'Unknown')
        
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['BB_Width'] = (df['Close'].rolling(20).std() * 4 / df['MA20']) * 100
        df['is_dropped'] = ((df['High'].rolling(252).max() - df['Close']) / df['High'].rolling(252).max()) > 0.25
        
        if mode == "מציאה" and df['is_dropped'].iloc[-1] and df['BB_Width'].iloc[-1] < 12:
            return {'Ticker': ticker, 'Score': 100, 'Sector': sector}
        elif mode == "פריצה" and df['BB_Width'].iloc[-1] < 15 and df['RVOL'].iloc[-1] > 1.2:
            score = min(100, int((15 - df['BB_Width'].iloc[-1]) * 3 + (df['RVOL'].iloc[-1] * 20)))
            return {'Ticker': ticker, 'Score': score, 'Sector': sector}
    except: return None
    return None

# --- ממשק משתמש ---
st.title("🛡️ TITAN: Multi-Strategy Scanner")

tab_brk, tab_val, tab_exp_brk, tab_exp_val = st.tabs([
    "🚀 סורק פריצות", "📉 סורק מציאות", "💡 הסבר: פריצות", "💡 הסבר: מציאות"
])

def run_and_display(mode, file_name):
    if st.button(f"סרוק מניות - {mode}"):
        with st.spinner("סורק את השוק..."):
            results = []
            with ThreadPoolExecutor(max_workers=50) as ex:
                futures = [ex.submit(run_scanner, t, mode) for t in get_universe()]
                for f in futures:
                    res = f.result()
                    if res: results.append(res)
            
            if results:
                df = pd.DataFrame(results)
                df.to_csv(file_name, index=False)
                st.session_state[mode] = df
            else: st.warning("לא נמצאו מניות.")

    if mode not in st.session_state and os.path.exists(file_name):
        st.session_state[mode] = pd.read_csv(file_name)
    
    if mode in st.session_state:
        df = st.session_state[mode]
        col1, col2, col3 = st.columns(3)
        col1.metric("סה\"כ מניות", len(df))
        col2.metric("סקטור דומיננטי", df['Sector'].mode()[0])
        
        st.dataframe(df, use_container_width=True)
        
        # כפתור הורדה לאקסל
        st.download_button(
            label="📥 הורד תוצאות ל-Excel",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f'TITAN_{mode}_results.csv',
            mime='text/csv'
        )
        
        if st.button(f"🗑️ נקה תוצאות {mode}"):
            if os.path.exists(file_name): os.remove(file_name)
            del st.session_state[mode]
            st.rerun()

with tab_brk: run_and_display("פריצה", "res_brk.csv")
with tab_val: run_and_display("מציאה", "res_val.csv")

with tab_exp_brk:
    st.markdown("### 🚀 אסטרטגיית פריצות (Breakout)")
    st.write("אסטרטגיה זו מחפשת מניות ב-'דחיסה' (Bollinger Squeeze). אנחנו מחפשים תנודתיות נמוכה (רצועות בולינגר צרות) יחד עם התפרצות בנפח המסחר (RVOL גבוה).")
    
with tab_exp_val:
    st.markdown("### 📉 אסטרטגיית מציאות (Mean Reversion)")
    st.write("אסטרטגיה זו מחפשת מניות שירדו לפחות 25% מהשיא שלהן ומתחילות להתייצב בבסיס תחתון, בהנחה שמדובר בתיקון לקראת עלייה.")
