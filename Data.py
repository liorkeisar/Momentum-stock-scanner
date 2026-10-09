
import math

import pandas as pd
import streamlit as st
import yfinance as yf


def _series(df, names):
    """Return the first matching row of a yfinance statement, newest first."""
    if df is None or getattr(df, "empty", True):
        return None
    for name in names:
        if name in df.index:
            s = df.loc[name].dropna()
            if len(s):
                return s.sort_index(ascending=False)
    return None


def _num(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def health_score(m):
    """0-100 score from debt, liquidity, cash flow, ROE and margins.
    Only the checks with available data count, so the score is scaled to what we know."""
    parts = []  # (points earned, max points)
    de = m.get("debt_to_equity")
    if de is not None:
        parts.append((25 if de < 50 else 12 if de < 100 else 0, 25))
    cr = m.get("current_ratio")
    if cr is not None:
        parts.append((20 if cr > 1.5 else 10 if cr > 1 else 0, 20))
    fcf = m.get("free_cash_flow")
    if fcf is not None:
        parts.append((25 if fcf > 0 else 0, 25))
    roe = m.get("roe")
    if roe is not None:
        parts.append((15 if roe > 0.15 else 8 if roe > 0.08 else 0, 15))
    pm = m.get("profit_margin")
    if pm is not None:
        parts.append((15 if pm > 0.10 else 8 if pm > 0.05 else 0, 15))
    possible = sum(p for _, p in parts)
    if possible == 0:
        return None
    return round(100 * sum(e for e, _ in parts) / possible)


def fair_value(m):
    """Average of a Graham number (if EPS and book value are positive) and the analyst mean target.
    This is a rough estimate, not a valuation model."""
    parts = []
    eps, bv = m.get("eps"), m.get("book_value")
    if eps and bv and eps > 0 and bv > 0:
        parts.append(("נוסחת גרהם", math.sqrt(22.5 * eps * bv)))
    if m.get("target_price"):
        parts.append(("יעד אנליסטים ממוצע", m["target_price"]))
    if not parts:
        return None, []
    return sum(v for _, v in parts) / len(parts), parts


@st.cache_data(ttl=3600, show_spinner=False)
def load_stock(ticker):
    ticker = ticker.upper().strip()
    t = yf.Ticker(ticker)
    info = t.info or {}

    price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
    if price is None:
        raise ValueError(f"לא נמצאו נתוני מחיר עבור {ticker}")

    fin = t.financials
    revenue = _series(fin, ["Total Revenue"])
    net_income = _series(fin, ["Net Income"])

    m = {
        "symbol": ticker,
        "name": info.get("longName") or ticker,
        "sector": info.get("sector") or "—",
        "price": price,
        "pe": _num(info.get("trailingPE")),
        "roe": _num(info.get("returnOnEquity")),
        "profit_margin": _num(info.get("profitMargins")),
        "revenue_growth": _num(info.get("revenueGrowth")),
        "debt_to_equity": _num(info.get("debtToEquity")),
        "current_ratio": _num(info.get("currentRatio")),
        "free_cash_flow": _num(info.get("freeCashflow")),
        "eps": _num(info.get("trailingEps")),
        "book_value": _num(info.get("bookValue")),
        "target_price": _num(info.get("targetMeanPrice")),
        "market_cap": _num(info.get("marketCap")),
        "beta": _num(info.get("beta")),
        "shares": _num(info.get("sharesOutstanding")),
        "total_debt": _num(info.get("totalDebt")) or 0.0,
        "total_cash": _num(info.get("totalCash")) or 0.0,
    }

    m["health"] = health_score(m)
    m["fair_value"], m["fv_parts"] = fair_value(m)
    m["upside"] = (m["fair_value"] / price - 1) if m["fair_value"] else None

    hist = t.history(period="1y")
    m["history"] = hist["Close"] if not hist.empty else None

    cols = {}
    if revenue is not None:
        cols["הכנסות"] = revenue
    if net_income is not None:
        cols["רווח נקי"] = net_income
    if cols:
        annual = pd.DataFrame(cols).head(4)
        annual.index = [pd.Timestamp(d).strftime("%Y") for d in annual.index]
        m["annual"] = annual
    else:
        m["annual"] = None

    return m
