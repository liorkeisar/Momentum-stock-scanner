# app.py
"""
Wyckoff Pro Swing Scanner - נקודת הכניסה הראשית.

הקובץ הזה מכיל רק: קונפיגורציה, טעינת CSS/כותרת, בניית הטאבים, ולוגיקת ה-UI
הספציפית של כל טאב (סינוני סיידבר, לולאת הסריקה, דוח מפורט). כל שאר הלוגיקה
(אינדיקטורים, חיזוי, שווי הוגן, מקורות נתונים, רכיבי תצוגה, התמדה) גרה תחת
modules/ - ראה שם אם אתה מחפש פונקציה ספציפית.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

from modules.styles import (
    configure_page, render_css, render_header, render_banner,
    render_bottom_nav, render_settings_panel,
    ACCENT, ACCENT_DARK, BG, PANEL, PANEL_ALT, BORDER, TEXT_MUTED, BUY_COLOR, SELL_COLOR,
)
from modules.utils import safe_last, is_bad, safe_div, safe_div_series, validate_df, fmt_compact_number
from modules.storage import (
    PORTFOLIO_FILE, SCAN_RESULTS_FILE, PREDICTIONS_FILE,
    get_csv_files_in_cwd, tickers_from_csv_file, load_tickers_from_folder,
    save_prediction_record, load_predictions, delete_prediction_tickers, clear_all_predictions,
    save_single_scan_result, load_saved_scan_results, delete_saved_scan_tickers, clear_all_saved_scans,
    get_portfolio_df, add_to_portfolio,
)
from modules.data_sources import (
    load_history, load_benchmark, load_market_indices, render_market_ticker,
    fetch_fear_greed_index, render_fear_greed_gauge,
    fetch_stock_news, fetch_analyst_data, render_news_and_analysts,
    load_sec_ticker_cik_map, fetch_insider_transactions,
)
from modules.indicators import add_indicators, compute_breakout_decision
from modules.ml_predictions import (
    train_logistic_model, logistic_predict_probability, backtest_score_calibration,
    statistical_similarity_prediction, pattern_detection_vcp_like,
)
from modules.ui_components import (
    score_color, score_badge_html, score_ring_big_html, sparkline_svg,
    render_stock_card, render_top_stat_cards, generate_rule_based_explanation,
    render_stat_pills, show_buttons, plot_advanced,
)
from modules.fair_value import fetch_fundamentals, render_fair_value_screen

# ============================
# קונפיגורציה + עיצוב גלובלי
# ============================
configure_page()
render_css()
render_header()
render_banner()

st.session_state.setdefault("app_theme", "dark")
st.session_state.setdefault("active_section", "scanner")

render_market_ticker()
render_fear_greed_gauge()

_active = st.session_state["active_section"]

if _active == "scanner":
    st.sidebar.header("⚙️ מקורות טיקרים לסורק")
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
                    tickers = dfu[col].dropna().astype(str).str.upper().str.strip().tolist()
                elif 'symbol' in cols:
                    col = [c for c in dfu.columns if c.strip().lower() == 'symbol'][0]
                    tickers = dfu[col].dropna().astype(str).str.upper().str.strip().tolist()
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

    with st.sidebar.expander("🎯 סינון ציון בסיסי", expanded=True):
        score_range = st.slider(
            "טווח ציון להצגה:", 0, 100, (60, 100),
            help="רק מניות עם ציון בטווח הזה יוצגו בתוצאות. הגבל את המקסימום כדי לסנן ציונים 'חשודים' גבוהים מדי, "
                 "או צמצם את המינימום כדי לראות גם מועמדים חלשים יותר."
        )
        min_score, max_score = score_range

        min_confidence = st.slider(
            "ביטחון מינימלי (%):", 0, 100, 0,
            help="אחוז הרכיבים בציון שהגיעו לרף 'חזק' (70+). מסנן איתותים עם ציון גבוה אך נתמכים ברכיב יחיד בלבד."
        )

    with st.sidebar.expander("🧪 סינוני איכות מתקדמים", expanded=False):
        exclude_broken_out = st.checkbox(
            "הסתר מניות שכבר פרצו (already broken out)", value=True,
            help="מסנן מניות שקיבלו את דגל הוטו 'כבר פרצה משמעותית' — למניעת False positives כמו CCO."
        )
        exclude_downtrend = st.checkbox(
            "הסתר מגמת-על יורדת (SMA200 יורד)", value=True,
            help="מסנן מניות עם מגמת-על שבורה (מתחת ל-SMA200 יורד) - סיכון גבוה גם אם רכיבים אחרים נראים טוב."
        )
        require_stage2 = st.checkbox(
            "דרוש Stage 2 מלא (Weinstein/Minervini)", value=False,
            help="מציג רק מניות שנמצאות במגמת-על בריאה מלאה: Close > SMA150 > SMA200 עולה."
        )
        rsi_range = st.slider(
            "טווח RSI:", 0, 100, (0, 100),
            help="סנן לפי RSI הנוכחי - לדוגמה 40-70 כדי להימנע ממניות overbought/oversold קיצוניות."
        )
        rvol_min = st.number_input(
            "נפח יחסי מינימלי (RVOL):", min_value=0.0, max_value=10.0, value=0.0, step=0.1,
            help="דורש שהנפח האחרון יהיה לפחות פי X מהממוצע ל-20 יום. 0 = ללא סינון."
        )
        atr_pct_range = st.slider(
            "טווח תנודתיות (ATR% מהמחיר):", 0.0, 15.0, (0.0, 15.0), step=0.5,
            help="מסנן מניות תנודתיות מדי (סיכון גבוה) או שקטות מדי (חסרות פוטנציאל תנועה)."
        )
        price_range = st.slider(
            "טווח מחיר ($):", 0, 1000, (0, 1000), step=5,
            help="הגבל לפי טווח מחיר המניה - לדוגמה כדי להימנע מ-penny stocks או ממניות יקרות מדי."
        )

    with st.sidebar.expander("⚙️ הגדרות סריקה", expanded=False):
        max_tickers = st.number_input("מקסימום טיקרים לסריקה:", min_value=10, max_value=1000, value=200, step=10)
        min_dollar_vol = st.number_input(
            "מינימום מחזור מסחר יומי ($):", min_value=0, max_value=100_000_000,
            value=2_000_000, step=500_000,
            help="מניות עם מחזור מסחר דולרי (מחיר × נפח ממוצע) נמוך מהסף יסוננו — נמנע מנזילות דלה שמעוותת אותות."
        )
        if st.button("🗑️ נקה מטמון (מחירים + SEC + CIK)", use_container_width=True):
            load_history.clear()
            load_benchmark.clear()
            load_market_indices.clear()
            load_sec_ticker_cik_map.clear()
            fetch_insider_transactions.clear()
            fetch_fear_greed_index.clear()
            fetch_stock_news.clear()
            fetch_analyst_data.clear()
            fetch_fundamentals.clear()
            st.success("המטמון נוקה — הריצה הבאה תביא נתונים עדכניים")

    st.sidebar.markdown("---")
    run_scan = st.sidebar.button("🚀 הרץ סריקת פריצה", use_container_width=True, type="primary")

    if run_scan:
        if not tickers:
            st.error("לא נבחרו טיקרים")
        else:
            tickers = list(dict.fromkeys(tickers))[:int(max_tickers)]  # ייחודיים בלבד + הגבלה
            results = []
            details = {}
            progress = st.progress(0, text="מתחיל סריקה...")
            total = len(tickers)
            errors = []
            skipped_liquidity = []

            benchmark_df = load_benchmark(period="12mo")

            for i, ticker in enumerate(tickers):
                progress.progress((i + 1) / total, text=f"בודק {ticker} ({i+1}/{total})")
                try:
                    df = load_history(ticker, period="12mo")
                    if df.empty:
                        results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                                         "Price": np.nan, "Note": "אין נתונים", "SavedAt": ""})
                        continue

                    avg_vol_20 = df["Volume"].tail(20).mean()
                    last_price_raw = safe_last(df["Close"])
                    dollar_vol = (avg_vol_20 * last_price_raw) if not is_bad(last_price_raw) else 0
                    if min_dollar_vol > 0 and dollar_vol < min_dollar_vol:
                        skipped_liquidity.append(ticker)
                        continue

                    if not is_bad(last_price_raw) and not (price_range[0] <= last_price_raw <= price_range[1]):
                        continue

                    df = add_indicators(df, benchmark_df=benchmark_df)
                    res = compute_breakout_decision(df)

                    if exclude_broken_out and res.get("already_broken_out"):
                        continue
                    if exclude_downtrend and res.get("hard_downtrend"):
                        continue
                    if require_stage2 and not res.get("stage2_ok"):
                        continue
                    rsi_last = res.get("rsi_last")
                    if not is_bad(rsi_last) and not (rsi_range[0] <= rsi_last <= rsi_range[1]):
                        continue
                    rvol_last = res.get("rvol_last")
                    if rvol_min > 0 and (is_bad(rvol_last) or rvol_last < rvol_min):
                        continue
                    atr_pct_last = res.get("atr_pct")
                    atr_pct_display = atr_pct_last * 100 if not is_bad(atr_pct_last) else np.nan
                    if not is_bad(atr_pct_display) and not (atr_pct_range[0] <= atr_pct_display <= atr_pct_range[1]):
                        continue
                    if res["confidence"] < min_confidence:
                        continue

                    last_close = safe_last(df["Close"])
                    results.append({
                        "Ticker": ticker,
                        "Score": res["score"],
                        "Confidence": res["confidence"],
                        "Risk": res["risk"],
                        "Price": round(float(last_close), 2) if not is_bad(last_close) else np.nan,
                        "Note": res["note"],
                        "SavedAt": ""
                    })
                    details[ticker] = {"res": res, "df_tail": df.tail(120)}
                except Exception as e:
                    results.append({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                                     "Price": np.nan, "Note": "שגיאה", "SavedAt": ""})
                    errors.append(f"{ticker}: {e}")

            progress.empty()
            if skipped_liquidity:
                st.caption(f"💧 {len(skipped_liquidity)} טיקרים סוננו בשל נזילות נמוכה מהסף שהוגדר: "
                            f"{', '.join(skipped_liquidity[:15])}{' ...' if len(skipped_liquidity) > 15 else ''}")
            if errors:
                with st.expander(f"⚠️ {len(errors)} טיקרים נכשלו בסריקה — לחץ לפרטים"):
                    for e in errors:
                        st.caption(e)

            st.session_state["scan_results"] = results
            st.session_state["scan_details"] = details
            st.session_state["last_min_score"] = min_score
            st.session_state["last_max_score"] = max_score

    if "scan_results" in st.session_state and st.session_state["scan_results"]:
        df_res_full = pd.DataFrame(st.session_state["scan_results"]).sort_values("Score", ascending=False).reset_index(drop=True)
        df_res = df_res_full[(df_res_full["Score"] >= min_score) & (df_res_full["Score"] <= max_score)]
        details = st.session_state.get("scan_details", {})

        if df_res.empty:
            st.info("לא נמצאו מניות מתאימות לפי הקריטריונים. נסה להרחיב את טווח הציון או להקל בסינוני האיכות בסיידבר.")
        else:
            df_res = df_res.copy()

            def _get_daily_chg(t):
                info = details.get(t)
                if info and not info["df_tail"].empty and "DailyChangePct" in info["df_tail"].columns:
                    v = safe_last(info["df_tail"]["DailyChangePct"])
                    return v if not is_bad(v) else 0.0
                return 0.0
            df_res["ChgPct"] = df_res["Ticker"].apply(_get_daily_chg)

            st.caption(f"נסרקו {len(df_res_full)} טיקרים · {len(df_res)} עומדים בסף הנוכחי")
            render_top_stat_cards(df_res, details)

            sort_choice = st.radio("מיין לפי:", ["ניקוד", "מחיר", "שינוי%"], horizontal=True, label_visibility="collapsed")
            if sort_choice == "מחיר":
                df_res = df_res.sort_values("Price", ascending=False)
            elif sort_choice == "שינוי%":
                df_res = df_res.sort_values("ChgPct", ascending=False)
            else:
                df_res = df_res.sort_values("Score", ascending=False)

            view_mode = st.radio("תצוגה:", ["🗂️ פיד", "📋 טבלה"], horizontal=True, label_visibility="collapsed")

            if view_mode == "🗂️ פיד":
                for _, row in df_res.iterrows():
                    t = row["Ticker"]
                    info = details.get(t)
                    if info:
                        render_stock_card(t, info["res"], info["df_tail"])
                    else:
                        render_stock_card(t, {"score": int(row["Score"]), "note": str(row["Note"])}, pd.DataFrame())
            else:
                st.dataframe(
                    df_res,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d"),
                        "Confidence": st.column_config.ProgressColumn("ביטחון", min_value=0, max_value=100, format="%d"),
                        "Risk": st.column_config.ProgressColumn("סיכון (נמוך=טוב)", min_value=0, max_value=100, format="%d"),
                        "Price": st.column_config.NumberColumn("מחיר", format="$%.2f"),
                    }
                )

            st.divider()
            col_save1, col_save2 = st.columns([3, 1])
            with col_save1:
                save_note = st.text_input("הערה לשמירה (אופציונלי):", "")
            with col_save2:
                st.write("")
                if st.button("💾 שמור תוצאות", use_container_width=True):
                    df_to_save = df_res.copy()
                    df_to_save["SavedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if save_note:
                        df_to_save["Note"] = df_to_save["Note"].astype(str) + " | " + save_note
                    header = not os.path.exists(SCAN_RESULTS_FILE)
                    df_to_save.to_csv(SCAN_RESULTS_FILE, mode='a', header=header, index=False)
                    st.success("תוצאות נשמרו בהצלחה")

            st.divider()
            col_select, col_buttons = st.columns([2, 1])
            with col_select:
                to_view = st.selectbox("בחר מניה לניתוח:", df_res['Ticker'].tolist())
            with col_buttons:
                st.write("")
                if st.button("➕ הוסף לתיק ההשקעות", use_container_width=True):
                    try:
                        price = df_res[df_res['Ticker'] == to_view]['Price'].values[0]
                    except Exception:
                        price = None
                    ok, msg = add_to_portfolio(to_view, price)
                    (st.success if ok else st.warning)(f"{to_view}: {msg}")

            st.subheader(f"🔎 דוח מפורט — {to_view}")
            info = details.get(to_view)
            if info:
                res = info["res"]
                m1, m2, m3 = st.columns(3)
                m1.metric("ציון פריצה", res["score"])
                m2.metric("ביטחון", f'{res["confidence"]}%')
                m3.metric("מדד סיכון", res["risk"])

                st.markdown(f"**סטטוס:** {score_badge_html(res['score'])}", unsafe_allow_html=True)

                with st.expander("📊 רכיבי ניקוד מפורטים"):
                    comp_labels = {
                        "compression": "דחיסת מחיר (Squeeze)",
                        "rvol": "נפח יחסי (RVOL)",
                        "trend": "טרנד EMA20/50",
                        "macd": "MACD",
                        "rsi": "RSI",
                        "institutional": "כסף מוסדי (OBV/AD)",
                        "proximity": "קרבה להתנגדות ישנה (לפני הריצה)",
                        "squeeze": "Squeeze פעיל כרגע",
                        "squeeze_duration": "משך ה-Squeeze",
                        "risk": "ניקוד סיכון (נמוך=טוב)",
                        "stage2": "מגמת-על (Stage 2)",
                        "relative_strength": "חוזק יחסי מול SPY",
                        "volume_quality": "איכות נפח (קונים/מוכרים)",
                        "extension": "התרחקות מהממוצע (Extension)",
                        "absorption": "איסוף בזמן ירידה (Wyckoff Absorption)",
                        "sideways": "תנועה הצידה (טווח, לא טרנד)",
                    }
                    comps_named = {comp_labels.get(k, k): v for k, v in res["components"].items()}
                    comp_df = pd.DataFrame.from_dict(comps_named, orient="index", columns=["ערך"]).sort_values("ערך", ascending=False)
                    st.dataframe(comp_df, use_container_width=True,
                                 column_config={"ערך": st.column_config.ProgressColumn("ערך", min_value=0, max_value=100, format="%d")})

                st.info(f"**הערות:** {res['note']}")

                with st.expander("🧠 הסבר מורחב — למה המניה קיבלה את הציון הזה? (חינמי, ללא AI בתשלום)", expanded=False):
                    st.caption("ההסבר נכתב אוטומטית מתוך רכיבי מנוע ההחלטה עצמו - בלי קריאה לשום שירות AI חיצוני/בתשלום.")
                    st.markdown(generate_rule_based_explanation(to_view, res))

                df_plot = info["df_tail"].copy()
                gc1, gc2, gc3, gc4 = st.columns(4)
                days_view = gc1.select_slider("טווח ימים בגרף", options=[30, 60, 90, 120], value=90, key=f"days_{to_view}")
                show_bands = gc2.checkbox("רצועות בולינגר", value=False, key=f"bands_{to_view}")
                show_macd = gc3.checkbox("MACD", value=False, key=f"macd_{to_view}")
                show_obv = gc4.checkbox("OBV", value=False, key=f"obv_{to_view}")
                st.plotly_chart(
                    plot_advanced(df_plot, to_view, show_macd=show_macd, show_obv=show_obv,
                                  show_bands=show_bands, days=days_view),
                    use_container_width=True
                )

                show_buttons(to_view)

                # ---------- שווי הוגן: קישור למסך הנפרד ----------
                st.markdown("---")
                fv_c1, fv_c2 = st.columns([3, 1])
                with fv_c1:
                    st.caption("💰 רוצה לבדוק אם המניה נסחרת מתחת/מעל לשווי ההוגן שלה (Graham / P/E / PEG / P/B / DCF)?")
                with fv_c2:
                    if st.button("💰 בדוק שווי הוגן", key=f"fv_btn_{to_view}", use_container_width=True):
                        st.session_state["fv_selected_ticker"] = to_view
                        st.session_state["fv_auto_run"] = True
                        st.success(f"✅ עבור לטאב '💰 שווי הוגן' למעלה כדי לראות את ניתוח השווי ההוגן של {to_view}")

                # ---------- חדשות ודירוגי אנליסטים ----------
                st.markdown("---")
                render_news_and_analysts(to_view)

                # ---------- חיזוי ----------
                st.markdown("---")
                st.markdown("### 🔮 חיזוי תנועות עבר")
                colp1, colp2 = st.columns([3, 1])
                with colp1:
                    lookahead = st.selectbox("חלון חיזוי (ימים):", [3, 5, 7], index=1, key=f"look_{to_view}")
                    stat_tol = st.slider("סף דמיון סטטיסטי (אחוזי שונות):", 5, 50, 15, key=f"tol_{to_view}")
                with colp2:
                    st.write("")
                    run_pred = st.button("הרץ חיזוי", key=f"pred_btn_{to_view}", use_container_width=True)

                if run_pred:
                    with st.spinner("מריץ חיזוי..."):
                        try:
                            hist_full = load_history(to_view, period="24mo")
                            if hist_full.empty:
                                st.error("אין היסטוריית מחירים מספקת לחיזוי")
                            else:
                                bench_full = load_benchmark(period="24mo")
                                hist_full = add_indicators(hist_full, benchmark_df=bench_full)
                                stat = statistical_similarity_prediction(hist_full, tolerance=stat_tol / 100.0, lookahead=lookahead)
                                pat = pattern_detection_vcp_like(hist_full)
                                model = train_logistic_model(hist_full)
                                ml_prob = logistic_predict_probability(model, hist_full)

                                if ml_prob is None:
                                    comps = res["components"]
                                    heur_weights = {"compression": 0.25, "rvol": 0.25, "trend": 0.2, "macd": 0.15, "proximity": 0.15}
                                    wsum = sum(comps.get(k, 0) * w for k, w in heur_weights.items())
                                    wtot = sum(heur_weights.values())
                                    ml_prob = float(min(0.99, max(0.01, wsum / (wtot * 100))))

                                st.success("חיזוי הושלם")
                                pc1, pc2, pc3 = st.columns(3)
                                pc1.metric("שיעור הצלחה סטטיסטי", f"{round(stat['rate']*100,1)}%", f"{stat['count']} מקרים דומים")
                                pc2.metric("תבנית VCP", "✅ נמצאה" if pat["match"] else "❌ לא נמצאה")
                                pc3.metric(f"הסתברות פריצה ({lookahead} ימים)", f"{round(ml_prob*100,1)}%")
                                st.caption(f"תבנית: {pat['desc']}")

                                rec = {
                                    "Ticker": to_view,
                                    "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "stat_count": stat["count"], "stat_successes": stat["successes"], "stat_rate": stat["rate"],
                                    "pattern_match": pat["match"], "pattern_desc": pat["desc"], "ml_prob": ml_prob
                                }
                                if save_prediction_record(rec):
                                    st.caption("✅ תחזית נשמרה ב-predictions.csv")

                                last_close_full = safe_last(hist_full["Close"])
                                scan_row = {
                                    "Ticker": to_view, "Score": res["score"], "Confidence": res["confidence"], "Risk": res["risk"],
                                    "Price": round(float(last_close_full), 2) if not is_bad(last_close_full) else np.nan,
                                    "Note": res["note"] + " | prediction",
                                    "SavedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                save_single_scan_result(scan_row)
                        except Exception as e:
                            st.error(f"שגיאה בהרצת חיזוי: {e}")

                # ---------- Backtest לכיול הציון ----------
                st.markdown("---")
                st.markdown("### 🧪 Backtest — האם הציון באמת עובד?")
                st.caption("בודק היסטורית: כשהמניה קיבלה ציון מסוים, כמה פעמים היא באמת פרצה תוך כמה ימים. "
                           "עוזר לכייל את 'טווח ציון להצגה' בסיידבר לספי ציון שבאמת מתאמים להצלחה.")
                bt_col1, bt_col2 = st.columns([3, 1])
                with bt_col1:
                    bt_lookahead = st.select_slider("חלון בדיקת פריצה (ימים):", options=[3, 5, 7, 10], value=5, key=f"bt_look_{to_view}")
                with bt_col2:
                    st.write("")
                    run_bt = st.button("הרץ Backtest", key=f"bt_btn_{to_view}", use_container_width=True)

                if run_bt:
                    with st.spinner("מריץ Backtest היסטורי... (עשוי לקחת כמה שניות)"):
                        bt_hist = load_history(to_view, period="5y")
                        if bt_hist.empty or len(bt_hist) < 300:
                            st.warning("אין מספיק היסטוריה (נדרשים לפחות ~300 ימי מסחר) להרצת Backtest אמין.")
                        else:
                            bt_bench = load_benchmark(period="5y")
                            bt_hist_full = add_indicators(bt_hist, benchmark_df=bt_bench)
                            summary, raw_bt = backtest_score_calibration(bt_hist_full, lookahead=bt_lookahead, step=3)
                            if summary is None or summary.empty:
                                st.warning("לא הצלחנו להריץ Backtest עבור טיקר זה (ייתכן חוסר בנתונים).")
                            else:
                                st.dataframe(
                                    summary, use_container_width=True, hide_index=True,
                                    column_config={
                                        "שיעור_הצלחה": st.column_config.ProgressColumn("שיעור הצלחה (%)", min_value=0, max_value=100, format="%.1f%%"),
                                        "מקרים": st.column_config.NumberColumn("מס' מקרים היסטוריים"),
                                    }
                                )
                                overall_rate = round(raw_bt["outcome"].mean() * 100, 1)
                                st.caption(f"שיעור פריצה כללי (בסיס להשוואה, ללא תלות בציון): **{overall_rate}%** "
                                           f"מתוך {len(raw_bt)} נקודות היסטוריות שנבדקו.")
                                st.info("💡 אם שיעור ההצלחה בדליים הגבוהים (70+) גבוה משמעותית מהשיעור הכללי — "
                                        "סימן שהציון אכן מוסיף ערך חיזוי עבור המניה הזו.")

                # ---------- אימות Insider Buying (SEC EDGAR) ----------
                st.markdown("---")
                st.markdown("### 🕵️ אימות קניות/מכירות Insider (SEC EDGAR)")
                st.caption("Form 4 הוא גילוי רגולטורי מחייב על עסקאות דירקטורים/מנהלים בכירים - "
                           "האות הכי 'חד משמעי' שאפשר לקבל בחינם על מישהו שקונה בכסף אמיתי משלו. "
                           "לא מבוצע אוטומטית בסריקה (כדי לא להעמיס על שרתי SEC) - רק לפי דרישה כאן.")
                ins_lookback = st.slider("טווח ימים לבדיקה:", 30, 365, 90, step=15, key=f"ins_look_{to_view}")
                run_insider = st.button("בדוק עסקאות Insider", key=f"insider_btn_{to_view}")

                if run_insider:
                    with st.spinner("שולף נתונים מ-SEC EDGAR..."):
                        ins = fetch_insider_transactions(to_view, lookback_days=ins_lookback, max_filings=25)

                    if ins.get("error"):
                        st.warning(f"⚠️ {ins['error']}")
                    elif ins["buys"] == 0 and ins["sells"] == 0:
                        st.info(f"לא נמצאו עסקאות Insider בשוק הפתוח ב-{ins_lookback} הימים האחרונים עבור טיקר זה.")
                    else:
                        ic1, ic2, ic3 = st.columns(3)
                        ic1.metric("קניות Insider", ins["buys"], f"${ins['buy_value']:,.0f}")
                        ic2.metric("מכירות Insider", ins["sells"], f"${ins['sell_value']:,.0f}")
                        net = ins["buy_value"] - ins["sell_value"]
                        ic3.metric("נטו (קנייה מינוס מכירה)", f"${net:,.0f}")

                        if ins["buys"] > 0 and ins["buy_value"] > ins["sell_value"]:
                            st.success("✅ קנייה נטו ע\"י אנשי פנים ב-90 הימים האחרונים — אישוש חיובי לתזה.")
                        elif ins["sells"] > ins["buys"] * 2:
                            st.caption("ℹ️ יש יותר מכירות מקניות - שים לב שמכירות insider הן לרוב שגרתיות "
                                       "(תוכניות 10b5-1, מימוש אופציות) ולא בהכרח סימן שלילי, בניגוד לקנייה "
                                       "בשוק הפתוח שהיא כמעט תמיד יזומה ומכוונת.")

                        tx_df = pd.DataFrame(ins["transactions"]).sort_values("date", ascending=False)
                        st.dataframe(
                            tx_df, use_container_width=True, hide_index=True,
                            column_config={
                                "date": "תאריך", "owner": "שם", "role": "תפקיד", "type": "סוג עסקה",
                                "shares": st.column_config.NumberColumn("מניות", format="%d"),
                                "value": st.column_config.NumberColumn("שווי ($)", format="$%.0f"),
                            }
                        )

            else:
                st.warning("אין פרטים לטיקר זה")

            st.divider()
            csv_data = df_res.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ הורד תוצאות כ-CSV", csv_data, file_name="decision_scan_results.csv", mime="text/csv")
    else:
        st.info("👈 בחר מקור טיקרים בסרגל הצד ולחץ על 'הרץ סריקת פריצה' כדי להתחיל.")

# --- טאב תיק ההשקעות ---
elif _active == "portfolio":
    st.subheader("💼 תיק ההשקעות שלי")
    portfolio = get_portfolio_df()

    with st.expander("➕ הוסף מניה ידנית לתיק"):
        with st.form("add_manual_stock_form", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns(3)
            new_ticker = fc1.text_input("טיקר").strip().upper()
            new_date = fc2.date_input("תאריך כניסה", value=datetime.now())
            new_price = fc3.number_input("מחיר כניסה", min_value=0.0, step=0.01, format="%.2f")
            submitted = st.form_submit_button("הוסף לתיק", use_container_width=True)
            if submitted:
                if not new_ticker:
                    st.warning("נא להזין טיקר")
                else:
                    new_row = pd.DataFrame({'Ticker': [new_ticker], 'Date': [new_date.strftime('%Y-%m-%d')], 'EntryPrice': [new_price]})
                    new_row.to_csv(PORTFOLIO_FILE, mode='a', header=not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) == 0, index=False)
                    st.success(f"{new_ticker} נוספה בהצלחה לתיק!")
                    st.rerun()

    if not portfolio.empty:
        with st.spinner("מעדכן מחירים נוכחיים..."):
            for i, row in portfolio.iterrows():
                try:
                    hist = yf.Ticker(row['Ticker']).history(period="1d")
                    if hist.empty:
                        raise ValueError("no data")
                    curr = float(hist['Close'].iloc[-1])
                    portfolio.loc[i, 'CurrentPrice'] = round(curr, 2)
                    entry = row['EntryPrice']
                    if not is_bad(entry) and float(entry) != 0:
                        portfolio.loc[i, 'Performance'] = round(((curr - float(entry)) / float(entry)) * 100, 2)
                    else:
                        portfolio.loc[i, 'Performance'] = np.nan
                except Exception:
                    portfolio.loc[i, 'CurrentPrice'] = np.nan
                    portfolio.loc[i, 'Performance'] = np.nan

        total_perf = portfolio['Performance'].dropna()
        if not total_perf.empty:
            pc1, pc2 = st.columns(2)
            pc1.metric("מספר החזקות", len(portfolio))
            pc2.metric("ביצוע ממוצע", f"{round(total_perf.mean(), 2)}%")

        st.dataframe(
            portfolio, use_container_width=True, hide_index=True,
            column_config={
                "EntryPrice": st.column_config.NumberColumn("מחיר כניסה", format="$%.2f"),
                "CurrentPrice": st.column_config.NumberColumn("מחיר נוכחי", format="$%.2f"),
                "Performance": st.column_config.NumberColumn("ביצוע %", format="%.2f%%"),
            }
        )

        st.divider()
        to_manage = st.selectbox("בחר מניה לניהול:", portfolio['Ticker'].tolist())
        show_buttons(to_manage)

        if st.button("🗑️ מחק מניה מהתיק"):
            portfolio_raw = get_portfolio_df()
            portfolio_raw = portfolio_raw[portfolio_raw['Ticker'] != to_manage]
            portfolio_raw.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{to_manage} הוסר מהתיק")
            st.rerun()
    else:
        st.info("התיק ריק. הוסף מניות מהסורק או ידנית למעלה.")

# --- טאב תחזיות שמורות ---
elif _active == "predictions":
    st.subheader("🔮 תחזיות שמורות")
    preds = load_predictions()
    if preds.empty:
        st.info("אין תחזיות שמורות כרגע.")
    else:
        st.dataframe(
            preds, use_container_width=True, hide_index=True,
            column_config={
                "stat_rate": st.column_config.ProgressColumn("שיעור הצלחה סטטיסטי", min_value=0, max_value=1, format="%.2f"),
                "ml_prob": st.column_config.ProgressColumn("הסתברות מודל", min_value=0, max_value=1, format="%.2f"),
            }
        )
        st.divider()
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            to_delete = st.multiselect("בחר טיקרים למחיקה מהתחזיות השמורות:", options=sorted(preds['Ticker'].unique().tolist()))
        with col_del2:
            st.write("")
            if st.button("מחק נבחרים", use_container_width=True):
                if not to_delete:
                    st.warning("לא נבחרו טיקרים למחיקה")
                elif delete_prediction_tickers(to_delete):
                    st.success("התחזיות נמחקו")
                    st.rerun()
                else:
                    st.error("שגיאה במחיקה")

        if st.button("נקה את כל התחזיות השמורות"):
            if clear_all_predictions():
                st.success("כל התחזיות נמחקו")
                st.rerun()
            else:
                st.error("שגיאה בניקוי הקובץ")

        csv_all = preds.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ הורד את כל התחזיות כ-CSV", csv_all, file_name="saved_predictions.csv", mime="text/csv")

        st.markdown("---")
        st.subheader("➕ הוספה מהתחזיות לתיק ההשקעות")
        saved_preds = sorted(preds['Ticker'].unique().tolist())
        pcol1, pcol2 = st.columns([3, 1])
        with pcol1:
            pick = st.selectbox("בחר טיקר להוספה לתיק:", saved_preds)
        with pcol2:
            st.write("")
            if st.button("הוסף לתיק", key="add_from_preds", use_container_width=True):
                try:
                    hist_full = load_history(pick, period="12mo")
                    last_close = safe_last(hist_full["Close"]) if not hist_full.empty else np.nan
                    price = round(float(last_close), 2) if not is_bad(last_close) else None
                    ok, msg = add_to_portfolio(pick, price)
                    (st.success if ok else st.warning)(f"{pick}: {msg}")
                except Exception as e:
                    st.error(f"שגיאה בהוספה לתיק: {e}")

# --- טאב ניהול תוצאות סריקה שמורות ---
elif _active == "saved_scans":
    st.subheader("🗂️ ניהול תוצאות סריקה שמורות")
    saved_scans = load_saved_scan_results()
    if saved_scans.empty:
        st.info("אין תוצאות סריקה שמורות.")
    else:
        st.dataframe(
            saved_scans, use_container_width=True, hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d"),
                "Confidence": st.column_config.ProgressColumn("ביטחון", min_value=0, max_value=100, format="%d"),
                "Price": st.column_config.NumberColumn("מחיר", format="$%.2f"),
            }
        )
        st.divider()
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            to_del = st.multiselect("בחר טיקרים למחיקה מקובץ הסריקות:", options=sorted(saved_scans['Ticker'].unique().tolist()))
        with col_del2:
            st.write("")
            if st.button("מחק נבחרים מסריקות", use_container_width=True):
                if not to_del:
                    st.warning("לא נבחרו טיקרים")
                elif delete_saved_scan_tickers(to_del):
                    st.success("הפריטים נמחקו מקובץ הסריקות")
                    st.rerun()
                else:
                    st.error("שגיאה במחיקה")

        if st.button("נקה את כל קובץ הסריקות"):
            if clear_all_saved_scans():
                st.success("קובץ הסריקות נוקה")
                st.rerun()
            else:
                st.error("שגיאה בניקוי הקובץ")

        csv_all_scans = saved_scans.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ הורד את כל הסריקות כ-CSV", csv_all_scans, file_name="saved_scans.csv", mime="text/csv")

# --- טאב שווי הוגן ---
elif _active == "fair_value":
    render_fair_value_screen()

elif _active == "settings":
    render_settings_panel()

# הניווט התחתון חייב להיקרא אחרון - ראה הערה ב-render_css() לגבי ה-CSS שתופס
# את שורת הכפתורים האחרונה בעמוד.
render_bottom_nav()
