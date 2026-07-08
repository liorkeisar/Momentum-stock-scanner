"""
portfolio.py
Wyckoff Pro v3

Portfolio management:
- Add stocks
- Remove stocks
- Track entry price
- Update current price
- Calculate profit/loss
"""

import os
import pandas as pd
import yfinance as yf

from datetime import datetime

from settings import PORTFOLIO_FILE
from utils import log, log_error



# =====================================================
# Create portfolio file
# =====================================================

def init_portfolio():

    if not os.path.exists(PORTFOLIO_FILE):

        df = pd.DataFrame(
            columns=[
                "Ticker",
                "Date",
                "EntryPrice"
            ]
        )

        df.to_csv(
            PORTFOLIO_FILE,
            index=False
        )



# =====================================================
# Load portfolio
# =====================================================

def load_portfolio():

    try:

        init_portfolio()

        return pd.read_csv(
            PORTFOLIO_FILE
        )


    except Exception as e:

        log_error(e)

        return pd.DataFrame()



# =====================================================
# Save portfolio
# =====================================================

def save_portfolio(df):

    try:

        df.to_csv(
            PORTFOLIO_FILE,
            index=False
        )

        return True


    except Exception as e:

        log_error(e)

        return False



# =====================================================
# Add stock
# =====================================================

def add_stock(
        ticker,
        entry_price=None):

    try:

        df = load_portfolio()


        ticker=ticker.upper()



        # prevent duplicate

        if ticker in df["Ticker"].values:

            return False



        if entry_price is None:

            data=yf.Ticker(
                ticker
            ).history(
                period="1d"
            )


            entry_price=float(
                data["Close"].iloc[-1]
            )



        new=pd.DataFrame({

            "Ticker":[ticker],

            "Date":[
                datetime.now()
                .strftime("%Y-%m-%d")
            ],

            "EntryPrice":[
                round(entry_price,2)
            ]

        })



        df=pd.concat(
            [
                df,
                new
            ],
            ignore_index=True
        )



        save_portfolio(
            df
        )


        return True



    except Exception as e:

        log_error(e)

        return False



# =====================================================
# Remove stock
# =====================================================

def remove_stock(ticker):

    try:

        df=load_portfolio()


        df=df[
            df["Ticker"]
            !=
            ticker.upper()
        ]


        save_portfolio(
            df
        )


        return True



    except Exception as e:

        log_error(e)

        return False



# =====================================================
# Get live price
# =====================================================

def get_price(ticker):

    try:

        data=yf.Ticker(
            ticker
        ).history(
            period="1d"
        )


        return float(
            data["Close"].iloc[-1]
        )


    except:

        return None



# =====================================================
# Update portfolio
# =====================================================

def update_portfolio():

    try:

        df=load_portfolio()


        if df.empty:

            return df



        current=[]

        performance=[]



        for _,row in df.iterrows():


            price=get_price(
                row["Ticker"]
            )


            current.append(
                price
            )


            if price:

                change=(

                    (price-row["EntryPrice"])
                    /
                    row["EntryPrice"]

                )*100


                performance.append(
                    round(change,2)
                )


            else:

                performance.append(
                    0
                )



        df["CurrentPrice"]=current

        df["Performance_%"]=performance



        save_portfolio(
            df
        )


        return df



    except Exception as e:

        log_error(e)

        return pd.DataFrame()



# =====================================================
# Portfolio statistics
# =====================================================

def portfolio_summary():

    try:

        df=update_portfolio()


        if df.empty:

            return {

                "stocks":0,

                "average_return":0,

                "winners":0,

                "losers":0

            }



        return {


            "stocks":
                len(df),


            "average_return":
                round(
                    df["Performance_%"]
                    .mean(),
                    2
                ),


            "winners":
                len(
                    df[
                    df["Performance_%"]>0
                    ]
                ),


            "losers":
                len(
                    df[
                    df["Performance_%"]<0
                    ]
                )

        }


    except:

        return {}
