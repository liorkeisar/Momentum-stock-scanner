"""
modules/ui_components.py
Wyckoff Pro Swing Scanner

רכיבי תצוגה גנריים לכרטיסי מניה, טבעות ציון, ספארקליין, גרף מחיר מפורט (Plotly),
הסבר מבוסס-כללים "למה המניה קיבלה את הציון הזה", וקישורי מקורות חיצוניים.
"""
import streamlit as st
import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from modules.utils import is_bad, safe_last, fmt_compact_number
from modules.styles import ACCENT, BUY_COLOR, SELL_COLOR, PANEL, PANEL_ALT, BORDER, TEXT_MUTED

def score_color(score):
    if score >= 75:
        return BUY_COLOR
    if score >= 55:
        return ACCENT
    return SELL_COLOR

def score_badge_html(score):
    color = score_color(score)
    return f'<span class="score-badge" style="background:{color}22; color:{color}; border:1px solid {color}55;">{score}</span>'

def ai_gauge_html(score):
    """טבעת ניקוד AI עגולה (conic-gradient) בסגנון SwingAI - ללא תלות בספריית גרפים חיצונית."""
    color = score_color(score)
    return f"""
    <div class="ai-gauge" style="background: conic-gradient({color} {score * 3.6}deg, {BORDER} 0deg);">
        <div class="ai-gauge-inner">
            <span class="score" style="color:{color};">{score}</span>
            <span class="lbl">AI</span>
        </div>
    </div>"""

def score_ring_big_html(score):
    """טבעת ציון גדולה ונקייה (בלי תווית 'AI') - מתאימה לכרטיס המעודכן בהשראת האפליקציה שהוצגה."""
    color = score_color(score)
    return f"""
    <div class="score-ring-big" style="background: conic-gradient({color} {score * 3.6}deg, {BORDER} 0deg);">
        <div class="score-ring-big-inner">
            <span class="score" style="color:{color};">{score}</span>
        </div>
    </div>"""

def sparkline_svg(values, color, width=280, height=44):
    vals = [v for v in values if not is_bad(v)]
    if len(vals) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pad = 3
    points = []
    for i, v in enumerate(vals):
        x = pad + (i / (n - 1)) * (width - 2 * pad)
        y = pad + (1 - (v - lo) / rng) * (height - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(points)
    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none">
        <polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.2"
                  stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

def classify_signal(score):
    if score >= 70:
        return "buy", "קנייה", ("גבוהה" if score >= 85 else "בינונית")
    if score <= 35:
        return "sell", "הימנעות", "גבוהה"
    return "neutral", "המתן", "נמוכה"

def compute_trade_levels(df_tail):
    try:
        entry = float(safe_last(df_tail["Close"]))
        atr = float(safe_last(df_tail["ATR"])) if "ATR" in df_tail.columns else np.nan
        recent_low = float(df_tail["Low"].tail(10).min())
        if is_bad(atr) or atr <= 0:
            stop = recent_low
        else:
            stop = min(recent_low, entry - 1.5 * atr)
        risk = entry - stop
        if is_bad(risk) or risk <= 0:
            return None
        target = entry + risk * 2.0
        rr = round((target - entry) / risk, 1)
        return {"entry": entry, "stop": stop, "target": target, "rr": rr}
    except Exception:
        return None

def render_stock_card(ticker, res, df_tail):
    score = res.get("score", 0)
    sig_class, sig_label, strength_label = classify_signal(score)
    tag_class = f"tag-{sig_class}"

    notes_list = [n.strip() for n in res.get("note", "").split(",") if n.strip()]
    notes_html = "".join(f"<div>• {n}</div>" for n in notes_list[:4])

    price_html, chg_html, spark_html, stat_row_html = "", "", "", ""
    if df_tail is not None and not df_tail.empty:
        last_price = safe_last(df_tail["Close"])
        chg_pct = safe_last(df_tail["DailyChangePct"]) if "DailyChangePct" in df_tail.columns else np.nan
        spark_vals = df_tail["Close"].tail(20).tolist()
        spark_color = BUY_COLOR if (not is_bad(chg_pct) and chg_pct >= 0) or (
            len(spark_vals) >= 2 and spark_vals[-1] >= spark_vals[0]) else SELL_COLOR
        spark_html = f'<div class="sparkline-wrap">{sparkline_svg(spark_vals, spark_color)}</div>'

        if not is_bad(last_price):
            price_html = f'<span class="stock-card-v2-price">${last_price:,.2f}</span>'
        if not is_bad(chg_pct):
            c_color = BUY_COLOR if chg_pct >= 0 else SELL_COLOR
            arrow = "▲" if chg_pct >= 0 else "▼"
            chg_html = f'<span class="stock-card-v2-chg" style="color:{c_color};">{arrow} {abs(chg_pct):.2f}%</span>'

        vol_last = safe_last(df_tail["Volume"]) if "Volume" in df_tail.columns else np.nan
        adx_last = safe_last(df_tail["ADX"]) if "ADX" in df_tail.columns else np.nan
        mfi_last = safe_last(df_tail["MFI"]) if "MFI" in df_tail.columns else np.nan
        rvol_last = safe_last(df_tail["RVOL"]) if "RVOL" in df_tail.columns else np.nan
        high52_last = safe_last(df_tail["High52W"]) if "High52W" in df_tail.columns else np.nan

        stat_row_html = f"""
        <div class="stat-row-v2">
            <div class="item"><div class="lbl">ווליום</div><div class="val">{fmt_compact_number(vol_last)}</div></div>
            <div class="item"><div class="lbl">ADX</div><div class="val">{f'{adx_last:.0f}' if not is_bad(adx_last) else '—'}</div></div>
            <div class="item"><div class="lbl">MFI</div><div class="val">{f'{mfi_last:.0f}' if not is_bad(mfi_last) else '—'}</div></div>
            <div class="item"><div class="lbl">RVOL</div><div class="val">{f'{rvol_last:.2f}x' if not is_bad(rvol_last) else '—'}</div></div>
            <div class="item"><div class="lbl">שיא 52ש'</div><div class="val">{f'${high52_last:,.1f}' if not is_bad(high52_last) else '—'}</div></div>
        </div>"""

    levels = compute_trade_levels(df_tail) if (df_tail is not None and not df_tail.empty) else None
    trade_html = ""
    if levels:
        trade_html = f"""
        <div class="stat-grid" style="margin-top:8px;">
            <div class="stat-box"><div class="lbl">כניסה</div><div class="val">${levels['entry']:.2f}</div></div>
            <div class="stat-box"><div class="lbl">סטופ</div><div class="val" style="color:{SELL_COLOR};">${levels['stop']:.2f}</div></div>
            <div class="stat-box"><div class="lbl">יעד</div><div class="val" style="color:{BUY_COLOR};">${levels['target']:.2f}</div></div>
            <div class="stat-box"><div class="lbl">R/R</div><div class="val" style="color:{ACCENT};">1:{levels['rr']}</div></div>
        </div>"""

    card_html = f"""
    <div class="stock-card-v2">
        <div class="stock-card-v2-top">
            <div style="flex:1; min-width:0;">
                <span class="stock-card-v2-ticker">{ticker}</span>
                <div style="margin-top:4px;">
                    <span class="tag {tag_class}">{sig_label}</span>
                    <span class="tag tag-strength">עוצמה: {strength_label}</span>
                </div>
                {spark_html}
                <div>{price_html}{chg_html}</div>
            </div>
            {score_ring_big_html(score)}
        </div>
        {stat_row_html}
        <div class="stock-note">{notes_html if notes_html else "אין אותות חזקים"}</div>
        {trade_html}
    </div>"""
    st.markdown(card_html, unsafe_allow_html=True)

def render_top_stat_cards(df_res, details):
    rising = falling = 0
    for t in df_res["Ticker"]:
        info = details.get(t)
        if not info or info["df_tail"].empty or "DailyChangePct" not in info["df_tail"].columns:
            continue
        chg = safe_last(info["df_tail"]["DailyChangePct"])
        if is_bad(chg):
            continue
        if chg >= 0:
            rising += 1
        else:
            falling += 1

    strong_breakout = int((df_res["Score"] >= 85).sum())
    avg_score = round(df_res["Score"].mean(), 0) if not df_res.empty else 0

    st.markdown(f"""
    <div class="top-stat-row">
        <div class="top-stat-card" style="background:rgba(34,197,94,0.10); border-color:rgba(34,197,94,0.30);">
            <div class="icon">📈</div>
            <div class="num" style="color:{BUY_COLOR};">{rising}</div>
            <div class="lbl">עולות</div>
        </div>
        <div class="top-stat-card" style="background:rgba(239,68,68,0.10); border-color:rgba(239,68,68,0.30);">
            <div class="icon">📉</div>
            <div class="num" style="color:{SELL_COLOR};">{falling}</div>
            <div class="lbl">יורדות</div>
        </div>
        <div class="top-stat-card" style="background:rgba(242,169,59,0.10); border-color:rgba(242,169,59,0.30);">
            <div class="icon">🚀</div>
            <div class="num" style="color:{ACCENT};">{strong_breakout}</div>
            <div class="lbl">פריצה חזקה</div>
        </div>
        <div class="top-stat-card" style="background:rgba(108,140,255,0.10); border-color:rgba(108,140,255,0.30);">
            <div class="icon">✨</div>
            <div class="num" style="color:#6c8cff;">{avg_score:.0f}</div>
            <div class="lbl">ציון ממוצע</div>
        </div>
    </div>""", unsafe_allow_html=True)

def generate_rule_based_explanation(ticker, res):
    comps = res.get("components", {})
    score = res.get("score", 0)
    confidence = res.get("confidence", 0)

    comp_meta = {
        "compression": ("דחיסת מחיר (Squeeze)", "המניה נמצאת בתקופת תנודתיות נמוכה יחסית להיסטוריה שלה - "
                        "מצב שלעיתים קרובות מקדים תנועה חדה, כי האנרגיה 'נאגרת' לפני פריצה."),
        "rvol": ("נפח יחסי (RVOL)", "הנפח האחרון ביחס לממוצע 20 היום - נפח גבוה מרמז על עניין מוגבר בשוק."),
        "trend": ("טרנד קצר טווח (EMA20/50)", "היחס בין הממוצע הנע ל-20 יום לממוצע ל-50 יום - EMA20 מעל EMA50 מרמז על מומנטום חיובי קצר-טווח."),
        "macd": ("MACD", "ההפרש בין קו ה-MACD לקו האיתות שלו - ערך חיובי וגדל מרמז על תאוצה חיובית במחיר."),
        "rsi": ("RSI", "מדד המומנטום הקלאסי - נבדק שהוא בטווח בריא (לא overbought/oversold קיצוני)."),
        "institutional": ("כסף מוסדי (OBV/AD)", "האם צבירת הנפח (OBV) וקו ההצטברות/חלוקה (AD) עולים ב-10 הימים האחרונים - סימן לכניסת כסף גדול."),
        "proximity": ("קרבה להתנגדות ישנה", "המרחק בין המחיר הנוכחי לרמת ההתנגדות שנוצרה *לפני* הריצה האחרונה - "
                      "ככל שהמחיר קרוב יותר מלמטה, כך הפוטנציאל ל'קדם-פריצה' אמיתי גבוה יותר."),
        "squeeze": ("Squeeze פעיל", "רצועות בולינגר בתוך ערוצי Keltner כרגע - איתות כיווץ תנודתיות קלאסי."),
        "squeeze_duration": ("משך ה-Squeeze", "כמה ימים רצופים המניה נמצאת במצב כיווץ - כיווץ ממושך יותר נוטה להוליד תנועה חדה יותר כשהוא נשבר."),
        "risk": ("ניקוד סיכון", "התנודתיות (ATR) כאחוז מהמחיר - ציון גבוה כאן = תנודתיות נמוכה יחסית = סיכון מחושב נמוך יותר."),
        "stage2": ("מגמת-על (Stage 2)", "לפי שיטת Weinstein/Minervini: מחיר מעל SMA150 שמעל SMA200 עולה = מגמת-על בריאה תומכת."),
        "relative_strength": ("חוזק יחסי מול SPY", "האם המניה השתפרה ביחס למדד S&P 500 ב-20 הימים האחרונים - חוזק יחסי הוא סימן מוביל חשוב."),
        "volume_quality": ("איכות נפח", "היחס בין נפח בימי עלייה לנפח בימי ירידה - יחס גבוה מרמז שהקונים דומיננטיים יותר מהמוכרים."),
        "extension": ("התרחקות מהממוצע (Extension)", "כמה יחידות ATR המחיר רחוק מ-EMA20 - מחיר קרוב לממוצע (לא 'מורחק') מעדיף כי זה מרמז שהתנועה עוד לא קרתה."),
        "absorption": ("איסוף שקט (Wyckoff Absorption)", "האם בימי ירידה המחיר נסגר קרוב לשיא הטווח היומי - סימן שקונים סופגים היצע בזמן חולשה, איתות איסוף קלאסי לפי וייקוף."),
        "sideways": ("תנועה הצידה (טווח אמיתי)", "שיפוע ה-EMA50 קרוב לאפס - מרמז על טווח מסחר אמיתי (לא טרנד תלול), הקרקע הקלאסית לבניית בסיס."),
    }

    strong = sorted([(k, v) for k, v in comps.items() if v >= 70], key=lambda x: -x[1])
    weak = sorted([(k, v) for k, v in comps.items() if v <= 30], key=lambda x: x[1])

    lines = []
    verdict = "חיובית מאוד" if score >= 80 else "חיובית" if score >= 65 else "מעורבת" if score >= 45 else "חלשה"
    lines.append(f"**סיכום כללי:** {ticker} קיבלה ציון **{score}/100** (רמת ביטחון {confidence}%), תמונה כללית {verdict}.")

    if strong:
        lines.append("\n**מה תומך בציון הגבוה:**")
        for k, v in strong[:6]:
            name, desc = comp_meta.get(k, (k, ""))
            lines.append(f"- **{name}** (ניקוד {v}/100): {desc}")

    if weak:
        lines.append("\n**מה מחליש את התמונה:**")
        for k, v in weak[:5]:
            name, desc = comp_meta.get(k, (k, ""))
            lines.append(f"- **{name}** (ניקוד {v}/100): {desc}")

    if res.get("hard_downtrend"):
        lines.append("\n⚠️ **וטו קשיח הופעל — מגמת-על יורדת:** המחיר מתחת ל-SMA200 שגם הוא יורד. "
                     "זהו סימן למגמת-על שבורה, ולכן הציון הסופי הוגבל (עוטה תקרה נמוכה) גם אם רכיבים אחרים חיוביים.")
    if res.get("already_broken_out"):
        dsb = res.get("days_since_breakout")
        extra = f" (לפני כ-{dsb} ימי מסחר)" if dsb is not None else ""
        lines.append(f"\n⚠️ **וטו קשיח הופעל — נראה שהמניה כבר פרצה{extra}:** זו כבר לא תבנית 'קדם-פריצה' טהורה - "
                     "המחיר כבר רחוק מדי מהבסיס/מהממוצעים, אז הציון הוגבל בהתאם כדי לא להטעות.")

    if not strong and not weak:
        lines.append("\nלא נמצאו רכיבים קיצוניים (לא חזקים ולא חלשים באופן מובהק) - תמונה ניטרלית למדי ברוב הפרמטרים.")

    lines.append("\n_הסבר זה נוצר אוטומטית מתוך ערכי הרכיבים של מנוע ההחלטה בלבד (ללא AI חיצוני/בתשלום), "
                  "ואינו מהווה ייעוץ השקעות._")
    return "\n".join(lines)

def render_stat_pills(df_res):
    buy_count = int((df_res["Score"] >= 70).sum())
    sell_count = int((df_res["Score"] <= 35).sum())
    total = len(df_res)
    st.markdown(f"""
    <div class="stat-pill-row">
        <div class="stat-pill"><div class="num" style="color:{BUY_COLOR};">{buy_count}</div><div class="lbl">קנייה</div></div>
        <div class="stat-pill"><div class="num" style="color:{SELL_COLOR};">{sell_count}</div><div class="lbl">הימנעות</div></div>
        <div class="stat-pill"><div class="num" style="color:{ACCENT};">{total}</div><div class="lbl">איתותים</div></div>
    </div>""", unsafe_allow_html=True)

def show_buttons(ticker):
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.link_button("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}", use_container_width=True)
    with c2: st.link_button("Finviz", f"https://finviz.com/quote.ashx?t={ticker}", use_container_width=True)
    with c3: st.link_button("Investing.com", f"https://www.investing.com/search/?q={ticker}", use_container_width=True)
    with c4: st.link_button("Webull", f"https://www.webull.com/quote/{ticker}", use_container_width=True)

def plot_advanced(df, ticker, show_macd=False, show_obv=False, show_bands=False, days=90):
    df = df.tail(days).copy()

    panels = ["price", "volume"]
    if show_macd:
        panels.append("macd")
    if show_obv:
        panels.append("obv")

    heights = {"price": 0.62, "volume": 0.18, "macd": 0.20, "obv": 0.20}
    total = sum(heights[p] for p in panels)
    row_heights = [heights[p] / total for p in panels]

    fig = make_subplots(rows=len(panels), cols=1, shared_xaxes=True,
                         vertical_spacing=0.04, row_heights=row_heights)
    row_of = {p: i + 1 for i, p in enumerate(panels)}

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="מחיר", increasing_line_color="#1fc46a", decreasing_line_color="#e2543b",
        increasing_fillcolor="#1fc46a", decreasing_fillcolor="#e2543b", line_width=1
    ), row=row_of["price"], col=1)

    if "MA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], line=dict(color="#f2c94c", width=1.6),
                                  name="ממוצע נע 20"), row=row_of["price"], col=1)

    if show_bands and "UpperBB" in df.columns and "LowerBB" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["UpperBB"], line=dict(color="#3d4a68", width=1),
                                  name="רצועה עליונה", showlegend=False), row=row_of["price"], col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["LowerBB"], line=dict(color="#3d4a68", width=1),
                                  name="רצועות בולינגר", fill='tonexty', fillcolor='rgba(108,140,255,0.06)'),
                      row=row_of["price"], col=1)

    vol_colors = np.where(df["Close"] >= df["Open"], "rgba(31,196,106,0.55)", "rgba(226,84,59,0.55)")
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="נפח", marker_color=vol_colors, showlegend=False),
                  row=row_of["volume"], col=1)

    if show_macd and "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#6c8cff", width=1.4)),
                      row=row_of["macd"], col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal", line=dict(color="#e2b93b", width=1.4)),
                      row=row_of["macd"], col=1)

    if show_obv and "OBV" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV", line=dict(color="#c88cff", width=1.4)),
                      row=row_of["obv"], col=1)

    fig.update_layout(
        height=460 + 130 * (len(panels) - 2),
        template="plotly_dark", paper_bgcolor="#131722", plot_bgcolor="#131722",
        font=dict(size=12, color="#c7cede"),
        legend=dict(orientation="h", y=1.05, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=30, b=10, l=10, r=10),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        bargap=0.15,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(title_text="מחיר", row=row_of["price"], col=1)
    fig.update_yaxes(title_text="נפח", row=row_of["volume"], col=1)

    return fig

