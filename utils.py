"""
utils.py
Wyckoff Pro v3

General utilities:
- Logging
- Retry
- Cache
- Data cleaning
- Helpers
"""

import os
import time
import json
import pickle
import logging
import hashlib
from datetime import datetime
from functools import wraps

import pandas as pd
import numpy as np

from settings import CACHE_DIR, LOG_DIR, DEBUG


# =====================================================
# Logging
# =====================================================

LOG_FILE = LOG_DIR / "wyckoff.log"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def log(message):

    logging.info(message)

    if DEBUG:
        print(message)



def log_error(error):

    logging.error(str(error))

    if DEBUG:
        print("ERROR:", error)



# =====================================================
# Retry Decorator
# =====================================================

def retry(
        attempts=3,
        delay=2):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            last_error = None

            for i in range(attempts):

                try:

                    return func(*args, **kwargs)

                except Exception as e:

                    last_error = e

                    log_error(e)

                    time.sleep(delay)


            raise last_error


        return wrapper

    return decorator



# =====================================================
# Cache System
# =====================================================

def create_hash(value):

    return hashlib.md5(
        str(value).encode()
    ).hexdigest()



def cache_file(name):

    return CACHE_DIR / f"{create_hash(name)}.cache"



def save_cache(name, data):

    try:

        path = cache_file(name)

        with open(path, "wb") as f:

            pickle.dump(data, f)

        return True


    except Exception as e:

        log_error(e)

        return False



def load_cache(name):

    try:

        path = cache_file(name)

        if not path.exists():

            return None


        with open(path, "rb") as f:

            return pickle.load(f)


    except Exception as e:

        log_error(e)

        return None



def clear_cache():

    try:

        for file in CACHE_DIR.iterdir():

            file.unlink()


        return True


    except Exception as e:

        log_error(e)

        return False



# =====================================================
# Data Helpers
# =====================================================

def clean_dataframe(df):

    if df is None:

        return pd.DataFrame()


    df = df.copy()


    df.replace(
        [np.inf, -np.inf],
        np.nan,
        inplace=True
    )


    df.dropna(
        inplace=True
    )


    return df



def safe_float(value):

    try:

        if value is None:

            return 0.0


        if np.isnan(value):

            return 0.0


        return float(value)


    except:

        return 0.0



def safe_int(value):

    try:

        return int(value)

    except:

        return 0



# =====================================================
# File Helpers
# =====================================================

def save_json(filename, data):

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )


        return True


    except Exception as e:

        log_error(e)

        return False




def load_json(filename):

    try:

        if not os.path.exists(filename):

            return {}


        with open(
            filename,
            encoding="utf-8"
        ) as f:

            return json.load(f)


    except Exception as e:

        log_error(e)

        return {}



# =====================================================
# Time Helpers
# =====================================================

def now():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )



# =====================================================
# Stock Helpers
# =====================================================

def normalize_ticker(ticker):

    if ticker is None:

        return ""

    return str(ticker).strip().upper()



def percentage_change(
        old,
        new):

    try:

        if old == 0:

            return 0


        return (
            (new-old)/old
        ) * 100


    except:

        return 0



# =====================================================
# Score Helpers
# =====================================================

def normalize_score(
        value,
        minimum=0,
        maximum=100):

    try:

        value = float(value)

        value = max(
            minimum,
            min(maximum,value)
        )

        return round(value,2)


    except:

        return 0



def signal_from_score(score):

    if score >= 85:

        return "STRONG BUY"


    if score >= 70:

        return "BUY"


    if score >= 50:

        return "WATCH"


    return "AVOID"
