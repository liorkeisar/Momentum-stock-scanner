"""
scanner.py
Wyckoff Pro v3

Stock scanner engine:
- Yahoo Finance data
- Multi-thread scanning
- Indicators
- Wyckoff analysis
"""

import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from settings import (
    DEFAULT_PERIOD,
    DEFAULT_INTERVAL,
    MAX_THREADS
)

from indicators import add_all_indicators
from wyckoff import calculate_wyckoff
from utils import (
    normalize_ticker,
    log,
    log_error,
    retry
)



# =====================================================
# Download Stock Data
# =====================================================

@retry(attempts=3, delay=2)
def download_stock(ticker):

    ticker = normalize_ticker(ticker)


    data = yf.download(
        ticker,
        period=DEFAULT_PERIOD,
        interval=DEFAULT_INTERVAL,
        progress=False,
        auto_adjust=True
    )


    if data.empty:

        return pd.DataFrame()



    # Yahoo sometimes returns multi index

    if isinstance(
        data.columns,
        pd.MultiIndex
    ):

        data.columns = data.columns.get_level_values(0)



    data.dropna(
        inplace=True
    )


    return data



# =====================================================
# Analyze Single Stock
# =====================================================

def analyze_stock(ticker):

    try:

        log(
            f"Scanning {ticker}"
        )


        df = download_stock(
            ticker
        )


        if df.empty:

            return None



        df = add_all_indicators(
            df
        )


        result = calculate_wyckoff(
            df
        )


        last = df.iloc[-1]



        output = {


            "ticker":ticker,


            "price":round(
                float(last["Close"]),
                2
            ),


            "wyckoff_score":
                result["wyckoff_score"],


            "phase":
                result["phase"],


            "smart_money":
                result["smart_money"],


            "spring":
                result["spring"],


            "sos":
                result["sos"],


            "lps":
                result["lps"],


            "signal":
                result["signal"],


        }



        return output



    except Exception as e:

        log_error(e)

        return None



# =====================================================
# Multi Thread Scanner
# =====================================================

def scan_market(
        tickers,
        workers=MAX_THREADS):


    results=[]


    tickers = [
        normalize_ticker(t)
        for t in tickers
    ]



    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:


        jobs = {

            executor.submit(
                analyze_stock,
                ticker
            ):ticker

            for ticker in tickers

        }



        for job in as_completed(jobs):

            result = job.result()


            if result:

                results.append(
                    result
                )



    if not results:

        return pd.DataFrame()



    df = pd.DataFrame(
        results
    )



    df.sort_values(
        by="wyckoff_score",
        ascending=False,
        inplace=True
    )


    return df



# =====================================================
# Filter Strong Candidates
# =====================================================

def filter_candidates(
        results,
        minimum_score=6):


    if results.empty:

        return results



    return results[
        results["wyckoff_score"]
        >=
        minimum_score
    ]



# =====================================================
# Example Test
# =====================================================

if __name__ == "__main__":


    symbols = [

        "AAPL",
        "MSFT",
        "NVDA",
        "TSLA"

    ]


    report = scan_market(
        symbols
    )


    print(report)
