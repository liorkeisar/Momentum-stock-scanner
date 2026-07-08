"""
database.py
Wyckoff Pro v3
"""

import pandas as pd
import sqlite3

from settings import (
    DATABASE_FILE,
    SCAN_RESULTS_FILE
)



# ==========================
# SQLite
# ==========================

def get_connection():

    return sqlite3.connect(
        DATABASE_FILE
    )



def init_database():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scans
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            score REAL,
            date TEXT
        )
        """
    )

    conn.commit()

    conn.close()



# ==========================
# Save scan results
# ==========================

def save_scan_results(df):

    if df is None or df.empty:
        return False


    try:

        df.to_csv(
            SCAN_RESULTS_FILE,
            index=False
        )

        return True

    except Exception:

        return False



# ==========================
# Load scan results
# ==========================

def load_scan_results():

    try:

        return pd.read_csv(
            SCAN_RESULTS_FILE
        )

    except Exception:

        return pd.DataFrame()



# ==========================
# Add single scan
# ==========================

def add_scan(
    ticker,
    score,
    date
):

    conn=get_connection()

    cursor=conn.cursor()


    cursor.execute(

        """
        INSERT INTO scans
        (ticker,score,date)

        VALUES (?,?,?)
        """,

        (
            ticker,
            score,
            date
        )

    )


    conn.commit()

    conn.close()
