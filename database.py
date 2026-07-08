"""
database.py
Wyckoff Pro v3

SQLite database manager
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from settings import DATABASE_FILE


# =====================================================
# Connection
# =====================================================

def get_connection():
    return sqlite3.connect(DATABASE_FILE)


# =====================================================
# Initialize Database
# =====================================================

def init_database():

    conn = get_connection()
    cur = conn.cursor()

    # ---------------------------
    # Scan Results
    # ---------------------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scan_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        price REAL,
        score INTEGER,
        wyckoff_score REAL,
        confidence REAL,
        risk REAL,
        signal TEXT,
        note TEXT,
        created_at TEXT
    )
    """)


    # ---------------------------
    # Predictions
    # ---------------------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        ticker TEXT NOT NULL,

        ml_probability REAL,

        statistical_probability REAL,

        pattern TEXT,

        prediction TEXT,

        created_at TEXT

    )
    """)


    # ---------------------------
    # Portfolio
    # ---------------------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        ticker TEXT NOT NULL,

        entry_price REAL,

        quantity REAL,

        stop_loss REAL,

        target_price REAL,

        status TEXT DEFAULT 'OPEN',

        entry_date TEXT

    )
    """)


    # ---------------------------
    # Watchlist
    # ---------------------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        ticker TEXT UNIQUE,

        added_date TEXT,

        note TEXT

    )
    """)


    # ---------------------------
    # Settings
    # ---------------------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (

        key TEXT PRIMARY KEY,

        value TEXT

    )
    """)


    # ---------------------------
    # Scan History
    # ---------------------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scan_history (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        ticker TEXT,

        action TEXT,

        score REAL,

        created_at TEXT

    )
    """)


    conn.commit()
    conn.close()



# =====================================================
# Generic Insert
# =====================================================

def execute(query, params=()):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(query, params)

    conn.commit()

    result = cur.lastrowid

    conn.close()

    return result



# =====================================================
# Scan Results
# =====================================================

def save_scan_result(data):

    query = """

    INSERT INTO scan_results

    (
    ticker,
    price,
    score,
    wyckoff_score,
    confidence,
    risk,
    signal,
    note,
    created_at
    )

    VALUES (?,?,?,?,?,?,?,?,?)

    """

    return execute(
        query,
        (
            data.get("ticker"),
            data.get("price"),
            data.get("score"),
            data.get("wyckoff_score"),
            data.get("confidence"),
            data.get("risk"),
            data.get("signal"),
            data.get("note"),
            datetime.now().isoformat()
        )
    )



def get_scan_results(limit=100):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM scan_results
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cur.fetchall()

    conn.close()

    return rows



def delete_scan_results():

    execute(
        "DELETE FROM scan_results"
    )



# =====================================================
# Portfolio
# =====================================================

def add_position(
        ticker,
        entry_price,
        quantity,
        stop_loss=None,
        target_price=None):


    return execute(

        """

        INSERT INTO portfolio

        (
        ticker,
        entry_price,
        quantity,
        stop_loss,
        target_price,
        entry_date
        )

        VALUES (?,?,?,?,?,?)

        """,

        (
            ticker,
            entry_price,
            quantity,
            stop_loss,
            target_price,
            datetime.now().isoformat()
        )

    )



def get_portfolio():

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM portfolio
        WHERE status='OPEN'
        """
    )

    rows = cur.fetchall()

    conn.close()

    return rows



def close_position(position_id):

    execute(

        """

        UPDATE portfolio

        SET status='CLOSED'

        WHERE id=?

        """,

        (position_id,)

    )



# =====================================================
# Watchlist
# =====================================================

def add_watchlist(ticker, note=""):

    return execute(

        """

        INSERT OR IGNORE INTO watchlist

        (
        ticker,
        added_date,
        note
        )

        VALUES (?,?,?)

        """,

        (
            ticker,
            datetime.now().isoformat(),
            note
        )

    )



def get_watchlist():

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT ticker,note
        FROM watchlist
        ORDER BY id DESC
        """
    )

    rows = cur.fetchall()

    conn.close()

    return rows



def remove_watchlist(ticker):

    execute(

        """
        DELETE FROM watchlist
        WHERE ticker=?
        """,

        (ticker,)

    )



# =====================================================
# Predictions
# =====================================================

def save_prediction(data):

    return execute(

        """

        INSERT INTO predictions

        (
        ticker,
        ml_probability,
        statistical_probability,
        pattern,
        prediction,
        created_at
        )

        VALUES (?,?,?,?,?,?)

        """,

        (

            data.get("ticker"),

            data.get("ml_probability"),

            data.get("statistical_probability"),

            data.get("pattern"),

            data.get("prediction"),

            datetime.now().isoformat()

        )

    )



def get_predictions(limit=100):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(

        """

        SELECT *

        FROM predictions

        ORDER BY id DESC

        LIMIT ?

        """,

        (limit,)

    )

    rows = cur.fetchall()

    conn.close()

    return rows



# =====================================================
# Application Start
# =====================================================

init_database()
