"""
modules/data_sources.py
Wyckoff Pro Swing Scanner

כל מקורות הנתונים החיצוניים: מחירים ומדדים (yfinance), מדד הפחד/תאוות בצע (CNN),
חדשות + המלצות אנליסטים (Yahoo Finance), ועסקאות Insider (SEC EDGAR Form 4).
כל פונקציה שמתחילה ב-fetch_/load_ שולפת נתונים גולמיים; כל render_ מציגה אותם.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import plotly.graph_objects as go

from modules.utils import is_bad
from modules.styles import ACCENT, PANEL, PANEL_ALT, BORDER, TEXT_MUTED, BUY_COLOR, SELL_COLOR, get_theme

@st.cache_data(ttl=300, show_spinner=False)
def load_history(ticker, period="12mo"):
    """
    טעינת היסטוריית מחירים. cache עם TTL של 5 דקות כדי למנוע נתונים תקועים לאורך זמן.

    כולל ניסיון חוזר קצר (עד 2 ניסיונות נוספים, עם השהיה עולה) - כי בסריקות
    מרוכזות של עשרות-מאות טיקרים, Yahoo Finance נוטה להגביל קצב (rate limit)
    על כתובת ה-IP המשותפת של Streamlit Cloud, מה שגורם לכישלונות זמניים
    שנפתרים לרוב בניסיון חוזר תוך שנייה-שתיים.
    """
    import time
    last_err = None
    for attempt in range(3):
        try:
            df = yf.Ticker(ticker).history(period=period)
            if df is not None and not df.empty:
                return df.dropna()
            last_err = "empty"
        except Exception as e:
            last_err = e
        if attempt < 2:
            time.sleep(0.6 * (attempt + 1))
    return pd.DataFrame()

BENCHMARK_TICKER = "SPY"

@st.cache_data(ttl=300, show_spinner=False)
def load_benchmark(period="24mo"):
    """טעינת מדד ייחוס (SPY) לחישוב חוזק יחסי."""
    return load_history(BENCHMARK_TICKER, period=period)

@st.cache_data(ttl=300, show_spinner=False)
def load_market_indices():
    """
    טוען מדדי שוק מרכזיים לשורת הטיקר העליונה (בהשראת עיצוב SwingAI).
    כל מדד: (מחיר אחרון, שינוי יומי ב-%). כשל בטיקר בודד לא מפיל את כל השורה.
    """
    indices = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX", "USD/ILS": "ILS=X"}
    out = {}
    for name, ticker in indices.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if len(hist) >= 2:
                last = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg_pct = ((last - prev) / prev * 100) if prev != 0 else 0.0
                out[name] = (last, chg_pct)
        except Exception:
            continue
    return out

def render_market_ticker():
    """מציג שורת כרטיסי מדדים עליונה, בסגנון SwingAI."""
    idx = load_market_indices()
    if not idx:
        return
    cards_html = ""
    for name, (val, chg) in idx.items():
        color = BUY_COLOR if chg >= 0 else SELL_COLOR
        sign = "+" if chg >= 0 else ""
        val_fmt = f"{val:,.2f}" if val < 100 else f"{val:,.0f}"
        cards_html += f"""
        <div class="ticker-card">
            <div class="ticker-name">{name}</div>
            <div class="ticker-val">{val_fmt}</div>
            <div class="ticker-chg" style="color:{color};">{sign}{chg:.2f}%</div>
        </div>"""
    st.markdown(f'<div class="ticker-row">{cards_html}</div>', unsafe_allow_html=True)

FNG_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

FNG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

FNG_RATING_HE = {
    "extreme fear": "פחד קיצוני",
    "fear": "פחד",
    "neutral": "ניטרלי",
    "greed": "תאוות בצע",
    "extreme greed": "תאוות בצע קיצונית",
}

FNG_RATING_COLOR = {
    "extreme fear": "#e0392b",
    "fear": "#f2994a",
    "neutral": "#f2d24c",
    "greed": "#a3c644",
    "extreme greed": "#27ae60",
}

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fear_greed_index():
    """שולף את מדד הפחד/תאוות הבצע העדכני של CNN (ציון 0-100 + דירוג + השוואות תקופתיות)."""
    try:
        r = requests.get(FNG_API_URL, headers=FNG_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        fg = data.get("fear_and_greed", {})
        if not fg or "score" not in fg or fg["score"] is None:
            return None
        return {
            "score": float(fg["score"]),
            "rating": str(fg.get("rating", "")).lower().strip(),
            "timestamp": fg.get("timestamp"),
            "previous_close": float(fg["previous_close"]) if fg.get("previous_close") is not None else None,
            "previous_1_week": float(fg["previous_1_week"]) if fg.get("previous_1_week") is not None else None,
            "previous_1_month": float(fg["previous_1_month"]) if fg.get("previous_1_month") is not None else None,
            "previous_1_year": float(fg["previous_1_year"]) if fg.get("previous_1_year") is not None else None,
        }
    except Exception:
        return None

def render_fear_greed_gauge():
    """מד-מחוג חצי-עיגולי של מדד הפחד/תאוות הבצע, בסגנון זהה לאפליקציית CNN Business."""
    fng = fetch_fear_greed_index()
    if not fng:
        st.info("⚠️ לא ניתן לטעון כרגע את מדד הפחד/תאוות הבצע (CNN) — ייתכן חסימת רשת זמנית. נסה 'נקה מטמון' בסיידבר.")
        return

    t = get_theme()
    score = fng["score"]
    rating = fng["rating"]
    rating_he = FNG_RATING_HE.get(rating, rating or "—")
    color = FNG_RATING_COLOR.get(rating, ACCENT)

    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": "rgba(0,0,0,0)", "thickness": 0},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 20], "color": "#e0392b"},
                {"range": [20, 40], "color": "#f2994a"},
                {"range": [40, 60], "color": "#f2d24c"},
                {"range": [60, 80], "color": "#a3c644"},
                {"range": [80, 100], "color": "#27ae60"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 5},
                "thickness": 0.82,
                "value": score,
            },
        }
    ))
    fig.update_layout(
        height=200,
        margin=dict(t=10, b=0, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text_secondary"]),
    )

    ago_txt = ""
    try:
        ts = pd.to_datetime(fng["timestamp"])
        now = pd.Timestamp.now(tz=ts.tzinfo) if ts.tzinfo is not None else pd.Timestamp.now()
        diff_sec = (now - ts).total_seconds()
        hours = int(diff_sec // 3600)
        minutes = int((diff_sec % 3600) // 60)
        ago_txt = f"לפני {hours} שעות" if hours >= 1 else f"לפני {max(minutes, 1)} דקות"
    except Exception:
        ago_txt = ""

    delta_html = ""
    prev_close = fng.get("previous_close")
    if prev_close is not None:
        delta = score - prev_close
        d_color = BUY_COLOR if delta >= 0 else SELL_COLOR
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<span style="color:{d_color}; font-weight:700;">{arrow} {abs(delta):.1f} נקודות</span>'

    top_html = f"""
    <div style="background:{t['panel']}; border:1px solid {t['border']}; border-radius:16px 16px 0 0;
                padding:14px 18px 0 18px; margin-top:2px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-weight:800; font-size:15px; color:{t['text_main']};">😨 מדד פחד ותאוות בצע — שוק המניות</div>
            <div style="font-size:11.5px; color:{t['text_muted']};">מקור: CNN</div>
        </div>
    </div>
    """
    st.markdown("".join(line.strip() for line in top_html.split("\n")), unsafe_allow_html=True)

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    bottom_html = f"""
    <div style="background:{t['panel']}; border:1px solid {t['border']}; border-top:none; border-radius:0 0 16px 16px;
                text-align:center; padding:0 18px 16px 18px; margin-top:-28px; margin-bottom:18px;">
        <div style="font-size:42px; font-weight:800; color:{t['text_main']}; line-height:1;">{score:.0f}</div>
        <div style="font-size:18px; font-weight:700; color:{color}; margin-top:2px;">{rating_he}</div>
        <div style="display:flex; justify-content:center; gap:14px; margin-top:8px; font-size:12.5px; color:{t['text_muted']};">
            <span>{ago_txt}</span>
            {delta_html}
        </div>
    </div>
    """
    st.markdown("".join(line.strip() for line in bottom_html.split("\n")), unsafe_allow_html=True)

    with st.expander("📊 השוואה לתקופות קודמות"):
        cols = st.columns(3)
        for col, (key, label) in zip(cols, [("previous_1_week", "לפני שבוע"), ("previous_1_month", "לפני חודש"), ("previous_1_year", "לפני שנה")]):
            val = fng.get(key)
            col.metric(label, f"{val:.0f}" if val is not None else "—")

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_stock_news(ticker, max_items=8):
    """
    שולף כותרות חדשות אחרונות עבור הטיקר. תומך בשני הפורמטים שיfinance
    מחזירה בגרסאות שונות (ישן: שדות שטוחים; חדש: מקונן תחת מפתח 'content').
    """
    try:
        raw = yf.Ticker(ticker).news or []
        items = []
        for it in raw[:max_items]:
            content = it.get("content", it) if isinstance(it, dict) else {}
            title = content.get("title") or (it.get("title") if isinstance(it, dict) else None)
            if not title:
                continue
            publisher = None
            provider = content.get("provider")
            if isinstance(provider, dict):
                publisher = provider.get("displayName")
            publisher = publisher or content.get("publisher") or it.get("publisher") or "מקור לא ידוע"
            link = None
            click_url = content.get("clickThroughUrl") or content.get("canonicalUrl")
            if isinstance(click_url, dict):
                link = click_url.get("url")
            link = link or it.get("link") or "#"
            pub_raw = content.get("pubDate") or content.get("displayTime") or it.get("providerPublishTime")
            items.append({"title": title, "publisher": publisher, "link": link, "pub_raw": pub_raw})
        return items
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_analyst_data(ticker):
    """שולף התפלגות המלצות אנליסטים (strongBuy/buy/hold/sell/strongSell) ויעדי מחיר, מ-Yahoo Finance."""
    result = {"recs": None, "targets": None, "error": None}
    try:
        t = yf.Ticker(ticker)
        try:
            rec_df = t.recommendations
            if rec_df is not None and not rec_df.empty:
                row = rec_df.iloc[0]
                result["recs"] = {
                    "strongBuy": int(row.get("strongBuy", 0) or 0),
                    "buy": int(row.get("buy", 0) or 0),
                    "hold": int(row.get("hold", 0) or 0),
                    "sell": int(row.get("sell", 0) or 0),
                    "strongSell": int(row.get("strongSell", 0) or 0),
                }
        except Exception:
            pass
        try:
            targets = t.analyst_price_targets
            if targets:
                result["targets"] = {
                    "current": targets.get("current"), "low": targets.get("low"),
                    "high": targets.get("high"), "mean": targets.get("mean"),
                }
        except Exception:
            pass
        if result["recs"] is None and result["targets"] is None:
            result["error"] = "אין נתוני אנליסטים זמינים למניה זו ב-Yahoo Finance"
        return result
    except Exception as e:
        result["error"] = f"שגיאה בשליפת נתוני אנליסטים: {e}"
        return result

def _news_time_ago(pub_raw):
    """ממיר חותמת זמן (unix timestamp או מחרוזת תאריך) ל'לפני X שעות' בעברית."""
    try:
        if pub_raw is None:
            return ""
        if isinstance(pub_raw, (int, float)):
            dt = datetime.fromtimestamp(pub_raw)
        else:
            dt = pd.to_datetime(pub_raw)
            if hasattr(dt, "tz_localize") and dt.tzinfo is not None:
                dt = dt.tz_localize(None)
        diff_h = (datetime.now() - dt).total_seconds() / 3600
        if diff_h < 1:
            return "לפני פחות משעה"
        if diff_h < 24:
            return f"לפני {int(diff_h)} שעות"
        return f"לפני {int(diff_h // 24)} ימים"
    except Exception:
        return ""

def render_news_and_analysts(ticker):
    """מציג כותרות חדשות אחרונות + התפלגות המלצות אנליסטים ויעדי מחיר, בסגנון Investing.com."""
    st.markdown("### 📰 חדשות ודירוגי אנליסטים")
    st.caption("נשלף מ-Yahoo Finance בזמן אמת (דרך yfinance) — לא מבוצע אוטומטית בסריקה כדי לא להעמיס.")
    if st.button("טען חדשות + המלצות אנליסטים", key=f"news_btn_{ticker}"):
        with st.spinner("שולף חדשות ונתוני אנליסטים..."):
            news_items = fetch_stock_news(ticker)
            analyst = fetch_analyst_data(ticker)

        t = get_theme()

        st.markdown("#### 📰 כותרות אחרונות")
        if not news_items:
            st.info("לא נמצאו כותרות חדשות עדכניות עבור טיקר זה.")
        else:
            for it in news_items:
                ago = _news_time_ago(it.get("pub_raw"))
                item_html = f"""
                <div style="background:{t['panel_alt']}; border:1px solid {t['border']}; border-radius:10px; padding:10px 14px; margin-bottom:8px;">
                    <a href="{it['link']}" target="_blank" style="color:{t['text_secondary']}; font-weight:700; font-size:13.5px; text-decoration:none;">{it['title']}</a>
                    <div style="color:{t['text_muted']}; font-size:11.5px; margin-top:4px;">{it['publisher']}{' · ' + ago if ago else ''}</div>
                </div>"""
                st.markdown("".join(line.strip() for line in item_html.split("\n")), unsafe_allow_html=True)

        st.markdown("#### 🎯 המלצות אנליסטים")
        if analyst.get("error") and not analyst.get("recs") and not analyst.get("targets"):
            st.info(analyst["error"])
        else:
            recs = analyst.get("recs")
            if recs and sum(recs.values()) > 0:
                total = sum(recs.values())
                bars_html = ""
                for label, val, color in [
                    ("קנייה חזקה", recs["strongBuy"], BUY_COLOR), ("קנייה", recs["buy"], "#6fcf97"),
                    ("החזקה", recs["hold"], ACCENT), ("מכירה", recs["sell"], "#f2994a"),
                    ("מכירה חזקה", recs["strongSell"], SELL_COLOR),
                ]:
                    pct = (val / total) * 100
                    bars_html += f"""
                    <div style="margin-bottom:6px;">
                        <div style="display:flex; justify-content:space-between; font-size:11.5px; color:{t['text_muted']};">
                            <span>{label}</span><span>{val}</span>
                        </div>
                        <div style="background:{t['border']}; border-radius:6px; height:8px; overflow:hidden;">
                            <div style="background:{color}; width:{pct:.0f}%; height:100%;"></div>
                        </div>
                    </div>"""
                st.markdown("".join(line.strip() for line in bars_html.split("\n")), unsafe_allow_html=True)
            else:
                st.caption("אין נתוני המלצות (Buy/Hold/Sell) זמינים למניה זו.")

            targets = analyst.get("targets")
            if targets and not is_bad(targets.get("mean")):
                tc1, tc2, tc3, tc4 = st.columns(4)
                tc1.metric("נוכחי", f"${targets['current']:.2f}" if not is_bad(targets.get('current')) else "—")
                tc2.metric("יעד נמוך", f"${targets['low']:.2f}" if not is_bad(targets.get('low')) else "—")
                tc3.metric("יעד ממוצע", f"${targets['mean']:.2f}" if not is_bad(targets.get('mean')) else "—")
                tc4.metric("יעד גבוה", f"${targets['high']:.2f}" if not is_bad(targets.get('high')) else "—")
            else:
                st.caption("אין יעדי מחיר אנליסטים זמינים למניה זו.")

SEC_USER_AGENT = "WyckoffProScanner/1.0 (contact: liorkeisar@gmail.com)"

@st.cache_data(ttl=86400, show_spinner=False)
def load_sec_ticker_cik_map():
    """טוען מיפוי טיקר -> CIK (מזהה חברה ב-SEC). מתעדכן פעם ביום - הקובץ עצמו משתנה לעיתים רחוקות."""
    try:
        headers = {"User-Agent": SEC_USER_AGENT}
        resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        mapping = {}
        for row in data.values():
            try:
                mapping[str(row["ticker"]).upper()] = str(row["cik_str"]).zfill(10)
            except Exception:
                continue
        return mapping
    except Exception:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_insider_transactions(ticker, lookback_days=90, max_filings=15):
    """
    שולף עסקאות Form 4 (קנייה/מכירה בשוק הפתוח ע"י דירקטורים/מנהלים) עבור טיקר,
    ישירות מ-SEC EDGAR. מחזיר dict עם סיכום קניות/מכירות ורשימת עסקאות בודדות.
    """
    result = {"buys": 0, "sells": 0, "buy_value": 0.0, "sell_value": 0.0, "transactions": [], "error": None}
    try:
        cik_map = load_sec_ticker_cik_map()
        if not cik_map:
            result["error"] = "לא ניתן להתחבר ל-SEC EDGAR כרגע (בעיית רשת או חסימה זמנית)"
            return result

        cik = cik_map.get(ticker.upper())
        if not cik:
            result["error"] = "לא נמצא מזהה CIK עבור טיקר זה ב-SEC (ייתכן שזו לא חברה אמריקאית רשומה)"
            return result

        headers = {"User-Agent": SEC_USER_AGENT}
        subs_resp = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers, timeout=10)
        subs_resp.raise_for_status()
        subs = subs_resp.json()

        recent = subs.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])

        cutoff = datetime.now() - timedelta(days=lookback_days)
        candidates = []
        for i, form in enumerate(forms):
            if form != "4":
                continue
            try:
                fdate = datetime.strptime(dates[i], "%Y-%m-%d")
            except Exception:
                continue
            if fdate < cutoff:
                continue
            candidates.append((fdate, accessions[i], docs[i]))

        candidates.sort(key=lambda x: x[0], reverse=True)
        candidates = candidates[:max_filings]

        cik_int = int(cik)
        for fdate, accession, doc in candidates:
            try:
                acc_nodash = accession.replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code != 200 or not r.content:
                    continue
                root = ET.fromstring(r.content)

                owner_name = ""
                owner_el = root.find(".//reportingOwner/reportingOwnerId/rptOwnerName")
                if owner_el is not None and owner_el.text:
                    owner_name = owner_el.text

                is_director = root.find(".//reportingOwner/reportingOwnerRelationship/isDirector")
                is_officer = root.find(".//reportingOwner/reportingOwnerRelationship/isOfficer")
                role_parts = []
                if is_director is not None and is_director.text == "1":
                    role_parts.append("דירקטור")
                if is_officer is not None and is_officer.text == "1":
                    role_parts.append("מנהל בכיר")
                role_str = "/".join(role_parts) if role_parts else "בעל עניין"

                for tx in root.findall(".//nonDerivativeTransaction"):
                    code_el = tx.find(".//transactionCoding/transactionCode")
                    shares_el = tx.find(".//transactionAmounts/transactionShares/value")
                    price_el = tx.find(".//transactionAmounts/transactionPricePerShare/value")
                    ad_el = tx.find(".//transactionAmounts/transactionAcquiredDisposedCode/value")
                    if code_el is None or code_el.text is None or shares_el is None or shares_el.text is None:
                        continue

                    code = code_el.text
                    try:
                        shares = float(shares_el.text)
                    except Exception:
                        continue
                    try:
                        price = float(price_el.text) if (price_el is not None and price_el.text) else 0.0
                    except Exception:
                        price = 0.0
                    ad = ad_el.text if (ad_el is not None and ad_el.text) else ""
                    value = shares * price

                    if code == "P" and ad == "A":
                        result["buys"] += 1
                        result["buy_value"] += value
                        result["transactions"].append({
                            "date": fdate.strftime("%Y-%m-%d"), "owner": owner_name, "role": role_str,
                            "type": "קנייה", "shares": shares, "value": value
                        })
                    elif code == "S" and ad == "D":
                        result["sells"] += 1
                        result["sell_value"] += value
                        result["transactions"].append({
                            "date": fdate.strftime("%Y-%m-%d"), "owner": owner_name, "role": role_str,
                            "type": "מכירה", "shares": shares, "value": value
                        })
            except Exception:
                continue

        return result
    except Exception as e:
        result["error"] = f"שגיאה בשליפת נתונים מ-SEC: {e}"
        return result

