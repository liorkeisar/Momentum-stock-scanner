"""
modules/fair_value.py
Wyckoff Pro Swing Scanner

מודל שווי הוגן רב-שיטתי: Graham המתוקן, P/E יחסי-היסטורי (IQR), PEGY (פיטר לינץ'),
P/B מוצדק לפי CAPM (Damodaran), ו-DCF דו-שלבי מהוון ב-WACC אמיתי. כולל את מסך
ה-UI הנפרד ("שווי הוגן") שמריץ את כל השיטות ומציג ממוצע משוקלל + חציון + פיזור.
"""
import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from modules.utils import is_bad, safe_last
from modules.styles import PANEL, ACCENT, BUY_COLOR, SELL_COLOR, get_theme
from modules.data_sources import load_history

EQUITY_RISK_PREMIUM = 0.045

DEFAULT_CREDIT_SPREAD = 0.02

DEFAULT_TAX_RATE = 0.21

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_risk_free_rate():
    """שולף תשואת אג\"ח ממשלת ארה\"ב ל-10 שנים (^TNX) כריבית חסרת סיכון ל-CAPM/WACC."""
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if hist is None or hist.empty:
            return 0.045
        last = float(hist["Close"].iloc[-1])
        rate = last / 10.0 / 100.0
        if rate <= 0 or rate > 0.20:
            return 0.045
        return rate
    except Exception:
        return 0.045

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fundamentals(ticker):
    """שולף נתוני יסוד (Fundamentals) מ-Yahoo Finance עבור מודל השווי ההוגן."""
    try:
        info = yf.Ticker(ticker).info or {}
        return {
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "trailingEps": info.get("trailingEps"),
            "forwardEps": info.get("forwardEps"),
            "bookValue": info.get("bookValue"),
            "priceToBook": info.get("priceToBook"),
            "earningsGrowth": info.get("earningsGrowth"),
            "revenueGrowth": info.get("revenueGrowth"),
            "earningsQuarterlyGrowth": info.get("earningsQuarterlyGrowth"),
            "freeCashflow": info.get("freeCashflow"),
            "operatingCashflow": info.get("operatingCashflow"),
            "totalDebt": info.get("totalDebt"),
            "totalCash": info.get("totalCash"),
            "sharesOutstanding": info.get("sharesOutstanding"),
            "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "marketCap": info.get("marketCap"),
            "beta": info.get("beta"),
            "returnOnEquity": info.get("returnOnEquity"),
            "payoutRatio": info.get("payoutRatio"),
            "dividendYield": info.get("dividendYield"),
        }
    except Exception:
        return {}

def compute_capm_cost_of_equity(beta, risk_free, erp=EQUITY_RISK_PREMIUM):
    b = beta if (not is_bad(beta) and beta > 0) else 1.0
    b = max(0.3, min(b, 3.0))
    return risk_free + b * erp

def compute_wacc(market_cap, total_debt, cost_of_equity, cost_of_debt, tax_rate=DEFAULT_TAX_RATE):
    try:
        E = market_cap if not is_bad(market_cap) and market_cap > 0 else 0.0
        D = total_debt if not is_bad(total_debt) and total_debt > 0 else 0.0
        if E + D <= 0:
            return cost_of_equity
        wacc = (E / (E + D)) * cost_of_equity + (D / (E + D)) * cost_of_debt * (1 - tax_rate)
        return max(0.03, min(wacc, 0.25))
    except Exception:
        return cost_of_equity

def compute_graham_revised(eps, growth_pct, aaa_yield_decimal):
    """נוסחת גרהם המתוקנת: V = [EPS × (8.5 + 2g) × 4.4] / Y."""
    try:
        if is_bad(eps) or eps <= 0 or is_bad(growth_pct):
            return None
        g = max(0.0, min(growth_pct, 30.0))
        y_pct = (aaa_yield_decimal * 100.0) if (not is_bad(aaa_yield_decimal) and aaa_yield_decimal > 0) else 4.4
        fair = (eps * (8.5 + 2 * g) * 4.4) / y_pct
        return fair if fair > 0 else None
    except Exception:
        return None

def compute_pe_relative(df_price, eps, current_pe):
    """P/E יחסי-היסטורי עם winsorization לפי IQR."""
    try:
        if is_bad(eps) or eps <= 0 or df_price is None or df_price.empty:
            return None
        hist_pe = (df_price["Close"] / eps).dropna()
        hist_pe = hist_pe[hist_pe > 0]
        if len(hist_pe) < 30:
            return None
        q1, q3 = hist_pe.quantile(0.25), hist_pe.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        clean_pe = hist_pe[(hist_pe >= lo) & (hist_pe <= hi)]
        if clean_pe.empty:
            clean_pe = hist_pe
        median_pe = clean_pe.median()
        fair_price = median_pe * eps
        return {"fair_price": fair_price, "median_pe": median_pe}
    except Exception:
        return None

def compute_peg_valuation_lynch(eps, growth_pct, dividend_yield_pct):
    """כלל ה-PEGY של פיטר לינץ': PE הוגן = קצב צמיחה + תשואת דיבידנד."""
    try:
        if is_bad(eps) or eps <= 0 or is_bad(growth_pct) or growth_pct <= 0:
            return None
        div_y = dividend_yield_pct if not is_bad(dividend_yield_pct) and dividend_yield_pct > 0 else 0.0
        fair_pe = growth_pct + div_y
        fair_price = eps * fair_pe
        return {"fair_price": fair_price, "fair_pe": fair_pe}
    except Exception:
        return None

def compute_justified_pb(roe, payout_ratio, cost_of_equity, bvps):
    """P/B מוצדק לפי מודל גורדון (Damodaran): Justified P/B = (ROE − g) / (r − g)."""
    try:
        if is_bad(roe) or is_bad(bvps) or bvps <= 0:
            return None
        payout = payout_ratio if (not is_bad(payout_ratio) and 0 <= payout_ratio <= 1) else 0.30
        g = roe * (1 - payout)
        g = max(0.0, min(g, cost_of_equity - 0.005))
        if cost_of_equity - g <= 0.001:
            return None
        justified_pb = (roe - g) / (cost_of_equity - g)
        if justified_pb <= 0 or justified_pb > 30:
            return None
        fair_price = justified_pb * bvps
        return {"fair_price": fair_price, "justified_pb": justified_pb, "sustainable_growth": g}
    except Exception:
        return None

def compute_dcf_valuation(fcf, growth_rate, discount_rate, terminal_growth, years, shares_outstanding, net_debt=0.0):
    """DCF דו-שלבי: דעיכה לינארית של קצב הצמיחה לכיוון הקצב הטרמינלי + ערך טרמינלי מהוון."""
    try:
        if is_bad(fcf) or fcf <= 0 or is_bad(shares_outstanding) or shares_outstanding <= 0:
            return None
        if discount_rate <= terminal_growth:
            return None
        pv_sum = 0.0
        cash_flow = fcf
        for yr in range(1, years + 1):
            g = growth_rate + (terminal_growth - growth_rate) * (yr / years)
            cash_flow = cash_flow * (1 + g)
            pv = cash_flow / ((1 + discount_rate) ** yr)
            pv_sum += pv
        terminal_value = cash_flow * (1 + terminal_growth) / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** years)
        enterprise_value = pv_sum + pv_terminal
        equity_value = enterprise_value - net_debt
        if equity_value <= 0:
            return None
        fair_price = equity_value / shares_outstanding
        return {"fair_price": fair_price, "enterprise_value": enterprise_value, "equity_value": equity_value}
    except Exception:
        return None

def compute_fair_value_report(ticker, df_price=None, growth_rate_override=None,
                               discount_rate_override=None, terminal_growth=0.025, dcf_years=10):
    """מריץ את כל 5 שיטות השווי ההוגן ומחזיר דוח מרוכז עם ממוצע משוקלל, חציון, ואזהרת פיזור."""
    fund = fetch_fundamentals(ticker)
    if not fund:
        return None

    current_price = fund.get("currentPrice")
    if is_bad(current_price) and df_price is not None and not df_price.empty:
        current_price = safe_last(df_price["Close"])
    if is_bad(current_price):
        return None

    eps = fund.get("trailingEps")
    bvps = fund.get("bookValue")
    current_pe = fund.get("trailingPE")
    if is_bad(current_pe) and not is_bad(eps) and eps > 0:
        current_pe = current_price / eps

    growth_pct = growth_rate_override
    if growth_pct is None:
        g = fund.get("earningsGrowth")
        if is_bad(g):
            g = fund.get("revenueGrowth")
        growth_pct = (g * 100) if not is_bad(g) else 10.0
    growth_pct = max(1.0, min(40.0, growth_pct))

    risk_free = fetch_risk_free_rate()
    beta = fund.get("beta")
    cost_of_equity = compute_capm_cost_of_equity(beta, risk_free)
    cost_of_debt = risk_free + DEFAULT_CREDIT_SPREAD
    market_cap = fund.get("marketCap")
    total_debt = fund.get("totalDebt") or 0.0
    total_cash = fund.get("totalCash") or 0.0
    net_debt = total_debt - total_cash

    wacc = compute_wacc(market_cap, total_debt, cost_of_equity, cost_of_debt)
    discount_rate = discount_rate_override if not is_bad(discount_rate_override) else wacc

    methods = {}

    graham = compute_graham_revised(eps, growth_pct, risk_free)
    if graham:
        methods["Graham מתוקן (EPS+צמיחה+תשואת אג\"ח)"] = {"fair_price": graham, "weight": 0.18}

    if df_price is not None and not df_price.empty:
        pe_rel = compute_pe_relative(df_price, eps, current_pe)
        if pe_rel:
            methods["P/E יחסי-היסטורי (IQR)"] = {"fair_price": pe_rel["fair_price"], "weight": 0.15}

    div_yield_pct = (fund.get("dividendYield") or 0.0) * 100 if not is_bad(fund.get("dividendYield")) else 0.0
    peg = compute_peg_valuation_lynch(eps, growth_pct, div_yield_pct)
    if peg:
        methods["PEGY (כלל פיטר לינץ')"] = {"fair_price": peg["fair_price"], "weight": 0.14}

    pb = compute_justified_pb(fund.get("returnOnEquity"), fund.get("payoutRatio"), cost_of_equity, bvps)
    if pb:
        methods["P/B מוצדק (CAPM · Damodaran)"] = {"fair_price": pb["fair_price"], "weight": 0.20}

    fcf = fund.get("freeCashflow") or fund.get("operatingCashflow")
    shares = fund.get("sharesOutstanding")
    dcf = compute_dcf_valuation(fcf, growth_pct / 100.0, discount_rate, terminal_growth, dcf_years, shares, net_debt)
    if dcf:
        methods["DCF דו-שלבי (WACC)"] = {"fair_price": dcf["fair_price"], "weight": 0.33}

    if not methods:
        return None

    for name, m in methods.items():
        fp = m["fair_price"]
        m["upside_pct"] = ((fp - current_price) / current_price) * 100 if current_price else None

    fair_prices = [m["fair_price"] for m in methods.values() if not is_bad(m["fair_price"]) and m["fair_price"] > 0]
    weights_sum = sum(m["weight"] for m in methods.values())
    weighted_avg = sum(m["fair_price"] * m["weight"] for m in methods.values()) / weights_sum if weights_sum > 0 else np.mean(fair_prices)
    median_fp = float(np.median(fair_prices)) if fair_prices else None

    dispersion_pct = None
    if len(fair_prices) >= 2 and weighted_avg:
        dispersion_pct = (float(np.std(fair_prices)) / weighted_avg) * 100

    avg_upside = ((weighted_avg - current_price) / current_price) * 100 if current_price and weighted_avg else None
    median_upside = ((median_fp - current_price) / current_price) * 100 if current_price and median_fp else None

    return {
        "ticker": ticker, "current_price": current_price, "eps": eps, "bvps": bvps,
        "current_pe": current_pe, "growth_pct": growth_pct, "methods": methods,
        "weighted_fair_price": weighted_avg, "avg_upside_pct": avg_upside,
        "median_fair_price": median_fp, "median_upside_pct": median_upside,
        "dispersion_pct": dispersion_pct,
        "risk_free": risk_free, "cost_of_equity": cost_of_equity, "wacc": wacc,
        "discount_rate_used": discount_rate, "fundamentals": fund,
    }

def render_fair_value_screen():
    """מסך שווי הוגן נפרד — 5 שיטות (Graham מתוקן, P/E יחסי, PEGY, P/B מוצדק-CAPM, DCF-WACC)."""
    st.subheader("💰 מסך שווי הוגן (Fair Value)")
    st.caption(
        "הערכת שווי הוגן משולבת מ-5 מודלים פיננסיים קלאסיים: Graham המתוקן, P/E יחסי-היסטורי, "
        "PEGY (פיטר לינץ'), P/B מוצדק לפי CAPM (Damodaran), ו-DCF דו-שלבי מהוון ב-WACC. "
        "⚠️ כלי תמיכה בהחלטה בלבד ואינו ייעוץ השקעות — כל הערכת שווי תלויה בהנחות (קצב צמיחה, ריבית היוון) "
        "שיכולות להשתנות ולסתור זו את זו."
    )

    default_ticker = st.session_state.get("fv_selected_ticker", "")
    fv_ticker = st.text_input("הזן טיקר לניתוח שווי הוגן:", value=default_ticker, key="fv_ticker_input").strip().upper()

    with st.expander("⚙️ הנחות מודל (ניתן לשנות — ברירת המחדל מבוססת CAPM/WACC אמיתיים)", expanded=False):
        rf_live = fetch_risk_free_rate()
        st.caption(f"ריבית חסרת סיכון נוכחית (תשואת אג\"ח ממשלת ארה\"ב ל-10 שנים, ^TNX): **{rf_live*100:.2f}%**")
        dc1, dc2, dc3 = st.columns(3)
        override_discount = dc1.checkbox("דרוס ריבית היוון (במקום WACC אוטומטי)", value=False)
        discount_rate_manual = dc1.slider("ריבית היוון ידנית %:", 5.0, 18.0, 10.0, step=0.5) / 100.0
        terminal_growth = dc2.slider("קצב צמיחה טרמינלי %:", 1.0, 4.0, 2.5, step=0.25) / 100.0
        dcf_years = dc3.select_slider("שנות תחזית DCF:", options=[5, 7, 10], value=10)
        use_auto_growth = st.checkbox("קצב צמיחה אוטומטי (מהערכת אנליסטים ב-Yahoo)", value=True)
        growth_override = st.slider("קצב צמיחת רווחים שנתי משוער % (אם לא אוטומטי):", 1.0, 40.0, 10.0, step=1.0)

    if not fv_ticker:
        st.info("הזן טיקר כדי להתחיל בניתוח שווי הוגן.")
        return

    run_clicked = st.button("🔍 חשב שווי הוגן", type="primary", use_container_width=True)
    auto_run = st.session_state.get("fv_auto_run", False) and fv_ticker == st.session_state.get("fv_selected_ticker")

    if run_clicked or auto_run:
        st.session_state["fv_auto_run"] = False
        with st.spinner(f"מחשב שווי הוגן עבור {fv_ticker}..."):
            df_price = load_history(fv_ticker, period="5y")
            report = compute_fair_value_report(
                fv_ticker, df_price=df_price,
                growth_rate_override=(None if use_auto_growth else growth_override),
                discount_rate_override=(discount_rate_manual if override_discount else None),
                terminal_growth=terminal_growth, dcf_years=dcf_years
            )
        st.session_state["fv_report"] = report
        st.session_state["fv_selected_ticker"] = fv_ticker

    report = st.session_state.get("fv_report")
    if not report or report.get("ticker") != fv_ticker:
        return

    cur_price = report["current_price"]
    w_fp = report["weighted_fair_price"]
    med_fp = report["median_fair_price"]
    avg_up = report["avg_upside_pct"]

    m1, m2, m3 = st.columns(3)
    m1.metric("מחיר נוכחי", f"${cur_price:,.2f}")
    m2.metric("שווי הוגן משוקלל", f"${w_fp:,.2f}" if not is_bad(w_fp) else "—")
    m3.metric("שווי הוגן — חציון", f"${med_fp:,.2f}" if not is_bad(med_fp) else "—")

    if not is_bad(avg_up):
        badge_color = BUY_COLOR if avg_up > 10 else (ACCENT if avg_up > -10 else SELL_COLOR)
        badge_text = f"{'מוערך בחסר ב-' if avg_up > 0 else 'מוערך ביתר ב-'}{abs(avg_up):.1f}%"
        st.markdown(f'<div style="text-align:center; margin: 10px 0;"><span class="score-badge" '
                    f'style="background:{badge_color}22; color:{badge_color}; border:1px solid {badge_color}55; font-size:16px;">{badge_text}</span></div>',
                    unsafe_allow_html=True)

    disp = report.get("dispersion_pct")
    if not is_bad(disp) and disp > 35:
        st.warning(f"⚠️ פיזור גבוה בין השיטות ({disp:.0f}%) — המודלים השונים לא מסכימים ביניהם משמעותית. "
                   f"התייחס לשווי ההוגן כאן בזהירות רבה יותר, ובדוק את הפירוט לפי שיטה למטה.")

    st.markdown("#### 📊 פירוט לפי שיטה")
    rows = []
    for name, m in report["methods"].items():
        rows.append({"שיטה": name, "משקל": f"{m['weight']*100:.0f}%",
                     "שווי הוגן": m["fair_price"], "פער מהמחיר הנוכחי %": m.get("upside_pct")})
    method_df = pd.DataFrame(rows)
    st.dataframe(
        method_df, use_container_width=True, hide_index=True,
        column_config={
            "שווי הוגן": st.column_config.NumberColumn(format="$%.2f"),
            "פער מהמחיר הנוכחי %": st.column_config.NumberColumn(format="%.1f%%"),
        }
    )

    fig = go.Figure()
    names = list(report["methods"].keys())
    vals = [m["fair_price"] for m in report["methods"].values()]
    colors_bars = [BUY_COLOR if v >= cur_price else SELL_COLOR for v in vals]
    fig.add_trace(go.Bar(x=names, y=vals, marker_color=colors_bars, name="שווי הוגן"))
    fig.add_hline(y=cur_price, line_dash="dash", line_color=ACCENT, annotation_text="מחיר נוכחי")
    t = get_theme()
    is_dark = t["bg"].lower() == "#0b0f17"
    fig.update_layout(height=340, template=("plotly_dark" if is_dark else "plotly_white"),
                      paper_bgcolor=t["panel"], plot_bgcolor=t["panel"],
                      font=dict(color=t["text_secondary"]), margin=dict(t=20, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔎 נתוני יסוד והנחות מודל ששימשו לחישוב"):
        fund = report["fundamentals"]
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("EPS (מייצג)", f"${report['eps']:.2f}" if not is_bad(report['eps']) else "—")
        fc2.metric("שווי נכסי למניה (BVPS)", f"${report['bvps']:.2f}" if not is_bad(report['bvps']) else "—")
        fc3.metric("P/E נוכחי", f"{report['current_pe']:.1f}" if not is_bad(report['current_pe']) else "—")
        fc4.metric("קצב צמיחה משוער", f"{report['growth_pct']:.1f}%")

        fc5, fc6, fc7 = st.columns(3)
        fc5.metric("ריבית חסרת סיכון (10Y)", f"{report['risk_free']*100:.2f}%")
        fc6.metric("עלות הון (CAPM)", f"{report['cost_of_equity']*100:.2f}%")
        fc7.metric("ריבית היוון בפועל", f"{report['discount_rate_used']*100:.2f}%",
                   help="WACC אוטומטי (משוקלל לפי חוב/הון), אלא אם נדרס ידנית בהגדרות למעלה.")
        st.caption("הנחות נוספות: פרמיית סיכון שוק (ERP) 4.5%, מרווח אשראי גנרי 2.0% מעל הריבית חסרת הסיכון, "
                   "שיעור מס חברות 21%, יחס אצירה שמרני של 30% אם לא ידוע מ-Yahoo Finance.")

    st.markdown(
        '<div class="top-banner">⚠️ הערכת שווי הוגן מבוססת על הנחות (קצב צמיחה, ריבית היוון, נתוני Yahoo Finance) '
        'ואינה תחזית מובטחת. שיטות שונות יכולות להניב תוצאות שונות מאוד באותה נקודת זמן — '
        'זהו כלי תמיכה בהחלטה בלבד ואינו מהווה ייעוץ השקעות.</div>',
        unsafe_allow_html=True
    )

