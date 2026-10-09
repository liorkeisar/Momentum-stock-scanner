import pandas as pd
import streamlit as st

import watchlist_store
from data import load_stock
from dcf import dcf_per_share

st.set_page_config(page_title="מודיעין מניות", page_icon="📈", layout="wide")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Heebo', sans-serif; }
.stApp { background: #0E1116; color: #E8E6E1; direction: rtl; }
h1, h2, h3 { font-weight: 800; }
[data-testid="stMetric"] {
    background: #161A22; border-right: 3px solid #F2A93B;
    padding: 12px 14px; border-radius: 4px;
}
.bar { height: 8px; background: #232833; border-radius: 4px; overflow: hidden; margin: 6px 0 14px; }
.bar > span { display: block; height: 100%; background: #F2A93B; }
.note { color: #8A8F98; font-size: 0.85rem; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

if "watchlist" not in st.session_state:
    st.session_state.watchlist = watchlist_store.load()


def pct(x):
    return None if x is None else round(x * 100, 1)


def fmt_price(x):
    return "—" if x is None else f"{x:,.2f}"


def fmt_pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def note(text):
    st.markdown(f'<p class="note">{text}</p>', unsafe_allow_html=True)


def health_bar(score):
    if score is None:
        note("אין מספיק נתונים לחישוב ציון בריאות")
        return
    st.markdown(f"**ציון בריאות פיננסית: {score}/100**")
    st.markdown(f'<div class="bar"><span style="width:{score}%"></span></div>', unsafe_allow_html=True)


def dcf_section(m):
    st.markdown("### מודל תזרים מהנכסים (DCF)")
    note("ההנחות ניתנות לשינוי. התוצאה רגישה מאוד לשיעור ההיוון ולצמיחה.")

    c = st.columns(3)
    growth = c[0].slider("צמיחת תזרים שנתית (5 שנים) %", -10, 40, 10, key="dcf_g") / 100
    terminal = c[1].slider("צמיחה לטווח ארוך %", 0.0, 4.0, 2.5, step=0.5, key="dcf_t") / 100
    discount = c[2].slider("שיעור היוון %", 6.0, 15.0, 9.0, step=0.5, key="dcf_d") / 100

    net_debt = (m["total_debt"] or 0) - (m["total_cash"] or 0)
    try:
        value, br = dcf_per_share(m["free_cash_flow"], growth, terminal, discount, m["shares"], net_debt)
    except ValueError as e:
        st.warning(str(e))
        return

    if value is None:
        st.info("לא ניתן לחשב DCF: תזרים חופשי שלילי או נתוני מניות חסרים.")
        return

    c = st.columns(3)
    c[0].metric("שווי DCF למניה", fmt_price(value))
    c[1].metric("מחיר שוק", fmt_price(m["price"]))
    c[2].metric("פער מהמחיר", fmt_pct(value / m["price"] - 1))
    with st.expander("פירוט החישוב"):
        st.write(f"ערך נוכחי של התזרימים לחמש שנים: {br['pv_flows']:,.0f}")
        st.write(f"ערך נוכחי של הערך לטווח ארוך: {br['pv_terminal']:,.0f}")
        st.write(f"שווי מניות לפני חוב נטו: {br['enterprise_value']:,.0f}")
        st.write(f"חוב נטו: {net_debt:,.0f}")
        note("התזרים החופשי מ-yfinance הוא קירוב. לניתוח מדויק בדוק את הדוחות המקוריים.")


def page_card():
    st.title("כרטיס מניה")
    ticker = st.text_input("סימול מניה", value="AAPL", key="card_ticker")
    if not ticker.strip():
        return

    try:
        m = load_stock(ticker)
    except Exception as e:
        st.error(f"לא הצלחנו לטעון את {ticker}. בדוק את הסימול. ({e})")
        return

    st.subheader(f"{m['name']} | {m['sector']}")

    c = st.columns(4)
    c[0].metric("מחיר", fmt_price(m["price"]))
    c[1].metric("שווי הוגן (הערכה)", fmt_price(m["fair_value"]))
    c[2].metric("פוטנציאל לעלייה", fmt_pct(m["upside"]))
    c[3].metric("מכפיל רווח (P/E)", fmt_price(m["pe"]))

    c = st.columns(4)
    c[0].metric("ROE", fmt_pct(m["roe"]))
    c[1].metric("מרווח רווח נקי", fmt_pct(m["profit_margin"]))
    c[2].metric("צמיחת הכנסות", fmt_pct(m["revenue_growth"]))
    c[3].metric("חוב להון", fmt_price(m["debt_to_equity"]))

    if m["fv_parts"]:
        with st.expander("איך חושב השווי ההוגן"):
            for name, value in m["fv_parts"]:
                st.write(f"{name}: {value:,.2f}")
            note("זוהי הערכה גסה בלבד.")

    health_bar(m["health"])

    dcf_section(m)

    if m["history"] is not None:
        st.markdown("**מחיר סגירה, שנה אחרונה**")
        st.line_chart(m["history"])

    if m["annual"] is not None:
        st.markdown("**נתונים שנתיים (במטבע הדיווח)**")
        st.dataframe(m["annual"])

    note("הנתונים מ-Yahoo Finance דרך yfinance ועשויים להתעכב. המידע להעשרה בלבד ואינו ייעוץ השקעות.")


DEFAULT_UNIVERSE = "AAPL, MSFT, NVDA, GOOGL, AMZN, META, JNJ, PG, KO, JPM, XOM, WMT"


def page_screener():
    st.title("סורק פונדמנטלי")
    raw = st.text_area("רשימת סימולים (מופרדים בפסיק)", DEFAULT_UNIVERSE)

    c = st.columns(5)
    max_pe = c[0].slider("P/E מקסימלי", 5, 80, 30)
    min_roe = c[1].slider("ROE מינימלי %", 0, 40, 10)
    min_growth = c[2].slider("צמיחת הכנסות מינימלית %", -20, 50, 5)
    min_health = c[3].slider("ציון בריאות מינימלי", 0, 100, 60)
    min_upside = c[4].slider("פוטנציאל לעלייה מינימלי %", -30, 100, 0)
    note("מניה שחסר בה נתון לאחד הסינונים לא תוצג.")

    if not st.button("סרוק"):
        return

    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
    rows = []
    bar = st.progress(0.0, text="סורק...")
    for i, tk in enumerate(tickers):
        bar.progress((i + 1) / len(tickers), text=f"טוען {tk}")
        try:
            m = load_stock(tk)
        except Exception:
            continue

        passes = (
            m["pe"] is not None and 0 < m["pe"] <= max_pe
            and m["roe"] is not None and m["roe"] * 100 >= min_roe
            and m["revenue_growth"] is not None and m["revenue_growth"] * 100 >= min_growth
            and m["health"] is not None and m["health"] >= min_health
            and m["upside"] is not None and m["upside"] * 100 >= min_upside
        )
        if passes:
            rows.append({
                "סימול": m["symbol"],
                "שם": m["name"],
                "מחיר": m["price"],
                "P/E": round(m["pe"], 1),
                "ROE %": pct(m["roe"]),
                "צמיחה %": pct(m["revenue_growth"]),
                "בריאות": m["health"],
                "פוטנציאל %": pct(m["upside"]),
            })
    bar.empty()

    if not rows:
        st.warning("אף מניה לא עברה את כל הסינונים. נסה להרפות את התנאים.")
        return

    df = pd.DataFrame(rows).sort_values("פוטנציאל %", ascending=False)
    st.success(f"נמצאו {len(df)} מניות מתוך {len(tickers)}")
    st.dataframe(df, hide_index=True)


COMPARE_ROWS = [
    ("מחיר", "price", fmt_price),
    ("P/E", "pe", fmt_price),
    ("ROE", "roe", fmt_pct),
    ("מרווח רווח נקי", "profit_margin", fmt_pct),
    ("צמיחת הכנסות", "revenue_growth", fmt_pct),
    ("חוב להון", "debt_to_equity", fmt_price),
    ("ציון בריאות", "health", lambda x: "—" if x is None else str(x)),
    ("שווי הוגן (הערכה)", "fair_value", fmt_price),
    ("פוטנציאל לעלייה", "upside", fmt_pct),
    ("בטא", "beta", fmt_price),
]


def page_compare():
    st.title("השוואה בין מניות")
    raw = st.text_input("סימולים להשוואה (עד 6, מופרדים בפסיק)", "AAPL, MSFT, GOOGL")
    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()][:6]
    if not tickers:
        return

    data, failed = {}, []
    for tk in tickers:
        try:
            data[tk] = load_stock(tk)
        except Exception:
            failed.append(tk)
    if failed:
        st.warning(f"לא נמצאו נתונים עבור: {', '.join(failed)}")
    if not data:
        return

    table = {}
    for label, key, fmt in COMPARE_ROWS:
        table[label] = {tk: fmt(m.get(key)) for tk, m in data.items()}
    st.dataframe(pd.DataFrame(table).T)
    note("מניה שחסר בה נתון מוצגת עם מקף.")


def page_watchlist():
    st.title("רשימת מעקב והתראות")

    with st.form("add_ticker", clear_on_submit=True):
        c = st.columns(4)
        tk = c[0].text_input("סימול")
        above = c[1].number_input("התראה: מחיר מעל", min_value=0.0, value=0.0, step=0.5)
        below = c[2].number_input("התראה: מחיר מתחת", min_value=0.0, value=0.0, step=0.5)
        submitted = c[3].form_submit_button("הוסף לרשימה")

    if submitted and tk.strip():
        st.session_state.watchlist[tk.strip().upper()] = {
            "above": above or None,
            "below": below or None,
        }
        watchlist_store.save(st.session_state.watchlist)

    if not st.session_state.watchlist:
        st.info("הרשימה ריקה. הוסף מניה כדי להתחיל.")
        return

    note("ההתראות נבדקות כשהאפליקציה נפתחת או מתרעננת. אין שליחה ברקע.")

    rows, alerts = [], []
    for tk, cfg in st.session_state.watchlist.items():
        try:
            m = load_stock(tk)
        except Exception:
            st.error(f"{tk}: לא נמצאו נתונים")
            continue

        price = m["price"]
        status = "בטווח"
        if cfg["above"] and price >= cfg["above"]:
            status = "מעל יעד ההתראה"
            alerts.append(f"{tk} הגיעה ל-{price:,.2f}, מעל {cfg['above']:,.2f}")
        if cfg["below"] and price <= cfg["below"]:
            status = "מתחת ליעד ההתראה"
            alerts.append(f"{tk} ירדה ל-{price:,.2f}, מתחת ל-{cfg['below']:,.2f}")

        rows.append({
            "סימול": tk,
            "מחיר": price,
            "התראה מעל": cfg["above"],
            "התראה מתחת": cfg["below"],
            "סטטוס": status,
            "בריאות": m["health"],
        })

    for msg in alerts:
        st.warning(msg)
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    to_remove = st.multiselect("הסר מהרשימה", list(st.session_state.watchlist.keys()))
    if st.button("הסר מניות נבחרות") and to_remove:
        for tk in to_remove:
            st.session_state.watchlist.pop(tk, None)
        watchlist_store.save(st.session_state.watchlist)
        st.rerun()


page = st.sidebar.radio("ניווט", ["כרטיס מניה", "סורק פונדמנטלי", "השוואה בין מניות", "רשימת מעקב והתראות"])
st.sidebar.caption("נתונים: Yahoo Finance דרך yfinance. אינו ייעוץ השקעות.")

if page == "כרטיס מניה":
    page_card()
elif page == "סורק פונדמנטלי":
    page_screener()
elif page == "השוואה בין מניות":
    page_compare()
else:
    page_watchlist()
