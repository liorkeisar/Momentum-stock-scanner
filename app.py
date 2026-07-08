"""
app.py
Wyckoff Pro v3

Main Streamlit Application
"""

import streamlit as st
import pandas as pd

from scanner import scan_market, filter_candidates
from indicators import add_all_indicators
from wyckoff import calculate_wyckoff
from ai import train_model, predict_breakout
from charts import create_stock_chart
from portfolio import (
    load_portfolio,
    add_stock,
    remove_stock,
    update_portfolio,
    portfolio_summary
)

from database import (
    save_scan_results,
    load_scan_results
)

from settings import APP_NAME



# =====================================================
# Page
# =====================================================

st.set_page_config(
    page_title=APP_NAME,
    layout="wide"
)


st.title(
    "◈ Wyckoff Pro AI Scanner"
)


st.caption(
    "מערכת סריקה מבוססת Wyckoff + AI + ניתוח טכני"
)



# =====================================================
# Sidebar
# =====================================================

st.sidebar.header(
    "⚙️ הגדרות סריקה"
)


tickers_text = st.sidebar.text_area(

    "רשימת מניות",

    "AAPL,MSFT,NVDA,TSLA"

)


tickers=[

    x.strip().upper()

    for x in tickers_text.split(",")

    if x.strip()

]



min_score = st.sidebar.slider(

    "ציון Wyckoff מינימלי",

    0,

    10,

    6

)



# =====================================================
# Tabs
# =====================================================

tab1,tab2,tab3,tab4 = st.tabs(

    [
        "📊 סורק",
        "📈 ניתוח מניה",
        "💼 תיק",
        "💾 היסטוריה"
    ]

)



# =====================================================
# Scanner
# =====================================================

with tab1:


    st.subheader(
        "סריקת שוק"
    )



    if st.button(
        "🚀 התחל סריקה"
    ):


        with st.spinner(
            "סורק מניות..."
        ):


            results = scan_market(
                tickers
            )


            if results.empty:

                st.warning(
                    "לא נמצאו נתונים"
                )


            else:


                filtered = filter_candidates(

                    results,

                    min_score

                )


                st.success(

                    f"נמצאו {len(filtered)} מועמדות"

                )


                st.dataframe(

                    filtered,

                    use_container_width=True

                )


                save_scan_results(
                    filtered
                )



# =====================================================
# Single Stock Analysis
# =====================================================

with tab2:


    ticker = st.text_input(

        "הכנס סימבול",

        "NVDA"

    ).upper()



    if st.button(

        "נתח מניה"

    ):


        import yfinance as yf



        df=yf.download(

            ticker,

            period="2y",

            auto_adjust=True,

            progress=False

        )



        if not df.empty:


            df=add_all_indicators(
                df
            )


            wyckoff = calculate_wyckoff(
                df
            )



            st.metric(

                "Wyckoff Score",

                f"{wyckoff['wyckoff_score']}/10"

            )


            st.write(

                wyckoff

            )



            chart=create_stock_chart(

                df,

                ticker,

                wyckoff

            )


            st.plotly_chart(

                chart,

                use_container_width=True

            )



            # AI


            if st.button(
                "🤖 אימון AI וחיזוי"
            ):


                model=train_model(
                    df
                )


                prediction=predict_breakout(

                    df,

                    model

                )


                st.success(

                    prediction

                )



        else:

            st.error(
                "לא נמצאו נתונים"
            )



# =====================================================
# Portfolio
# =====================================================

with tab3:


    st.subheader(
        "תיק השקעות"
    )


    portfolio=update_portfolio()



    if not portfolio.empty:


        st.dataframe(

            portfolio,

            use_container_width=True

        )


    summary=portfolio_summary()


    st.write(

        summary

    )



    st.divider()



    new_stock=st.text_input(

        "הוסף מניה"

    )



    if st.button(

        "הוסף לתיק"

    ):


        if new_stock:


            if add_stock(
                new_stock
            ):

                st.success(
                    "נוסף לתיק"
                )



    delete_stock=st.text_input(

        "מחק מניה"

    )



    if st.button(

        "מחיקה"

    ):


        remove_stock(
            delete_stock
        )

        st.success(
            "נמחק"
        )



# =====================================================
# History
# =====================================================

with tab4:


    st.subheader(
        "סריקות שמורות"
    )


    history=load_scan_results()


    if history.empty:

        st.info(
            "אין היסטוריה"
        )

    else:

        st.dataframe(

            history,

            use_container_width=True

        )
