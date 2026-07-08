"""
database.py
Wyckoff Pro v3
"""

import os
import pandas as pd

from settings import SCAN_RESULTS_FILE


def save_scan_results(df):

    try:

        if df is None or df.empty:
            return False

        df.to_csv(
            SCAN_RESULTS_FILE,
            index=False
        )

        return True

    except Exception as e:

        print("Database save error:", e)

        return False



def load_scan_results():

    try:

        if not os.path.exists(SCAN_RESULTS_FILE):
            return pd.DataFrame()

        return pd.read_csv(
            SCAN_RESULTS_FILE
        )

    except Exception as e:

        print("Database load error:", e)

        return pd.DataFrame()



def clear_scan_results():

    try:

        if os.path.exists(SCAN_RESULTS_FILE):

            os.remove(
                SCAN_RESULTS_FILE
            )

        return True

    except:

        return False
