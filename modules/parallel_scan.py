"""
modules/parallel_scan.py

Parallel scanning helper for Momentum-stock-scanner.
Provides run_parallel_scan(...) which executes the per-ticker pipeline in parallel
and returns structured results and details similar to the previous serial loop.

Design goals:
- Keep behavior compatible with existing filters and post-processing.
- Use ThreadPoolExecutor with configurable max_workers and simple batching to
  reduce risk of hitting rate limits.
- Collect detailed logs for failures and reasons for filtering.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import List, Dict, Tuple

import numpy as np

from modules.data_sources import load_history, load_benchmark
from modules.indicators import add_indicators, compute_breakout_decision, compute_wyckoff_phase
from modules.utils import is_bad, safe_last


def _process_one(ticker: str, benchmark_df, price_range, min_dollar_vol,
                 exclude_broken_out, exclude_downtrend, require_stage2,
                 rsi_range, rvol_min, atr_pct_range) -> Tuple[dict, dict, str]:
    """Process a single ticker and return (result_row, details_entry, error_msg).
    result_row follows the previous format appended to results list.
    details_entry contains res, df_tail and phase if available.
    error_msg is None when succeeded or a short string on failure.
    """
    try:
        df = load_history(ticker, period="12mo")
        if df is None or df.empty:
            return ({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                     "Price": np.nan, "Note": "אין נתונים", "SavedAt": ""}, {}, None)

        avg_vol_20 = df["Volume"].tail(20).mean()
        last_price_raw = safe_last(df["Close"])
        dollar_vol = (avg_vol_20 * last_price_raw) if not is_bad(last_price_raw) else 0
        if min_dollar_vol > 0 and dollar_vol < min_dollar_vol:
            # signal to skip due to low liquidity
            return (None, None, "low_liquidity")

        if not is_bad(last_price_raw) and not (price_range[0] <= last_price_raw <= price_range[1]):
            return (None, None, "price_range")

        df = add_indicators(df, benchmark_df=benchmark_df)
        res = compute_breakout_decision(df)

        if exclude_broken_out and res.get("already_broken_out"):
            return (None, None, "already_broken_out")
        if exclude_downtrend and res.get("hard_downtrend"):
            return (None, None, "hard_downtrend")
        if require_stage2 and not res.get("stage2_ok"):
            return (None, None, "stage2")

        rsi_last = res.get("rsi_last")
        if not is_bad(rsi_last) and not (rsi_range[0] <= rsi_last <= rsi_range[1]):
            return (None, None, "rsi")

        rvol_last = res.get("rvol_last")
        if rvol_min > 0 and (is_bad(rvol_last) or rvol_last < rvol_min):
            return (None, None, "rvol")

        atr_pct_last = res.get("atr_pct")
        atr_pct_display = atr_pct_last * 100 if not is_bad(atr_pct_last) else np.nan
        if not is_bad(atr_pct_display) and not (atr_pct_range[0] <= atr_pct_display <= atr_pct_range[1]):
            return (None, None, "atr")

        if res["confidence"] < 0:  # keep compatibility guard (shouldn't happen)
            return (None, None, "confidence")

        last_close = safe_last(df["Close"])
        row = {
            "Ticker": ticker,
            "Score": res.get("score", 0),
            "Confidence": res.get("confidence", 0),
            "Risk": res.get("risk", 100),
            "Price": round(float(last_close), 2) if not is_bad(last_close) else np.nan,
            "Note": res.get("note", ""),
            "SavedAt": ""
        }
        details = {ticker: {"res": res, "df_tail": df.tail(120), "phase": compute_wyckoff_phase(df)}}
        return (row, details[ticker], None)

    except Exception as e:
        return ({"Ticker": ticker, "Score": 0, "Confidence": 0, "Risk": 100,
                 "Price": np.nan, "Note": "שגיאה", "SavedAt": ""}, {}, f"error:{e}")


def run_parallel_scan(tickers: List[str], max_workers: int = 10, batch_sleep: float = 0.2,
                      price_range=(0, 1000), min_dollar_vol=0,
                      exclude_broken_out=True, exclude_downtrend=True, require_stage2=False,
                      rsi_range=(35, 75), rvol_min=0.8, atr_pct_range=(2.0, 6.0)) -> Tuple[List[dict], Dict[str, dict], dict]:
    """Run the scanning pipeline in parallel and return (results, details, meta).

    meta contains counters: filtered_reasons, skipped_liquidity, errors, no_data_count, total
    """
    benchmark_df = load_benchmark(period="12mo")

    results = []
    details = {}
    errors = []
    skipped_liquidity = []
    no_data_count = 0
    filtered_reasons = {
        "already_broken_out": 0, "hard_downtrend": 0, "stage2": 0,
        "rsi": 0, "rvol": 0, "atr": 0, "confidence": 0, "price_range": 0,
    }

    total = len(tickers)
    # Simple batching loop to avoid blasting the data provider
    batch_size = max(1, max_workers * 3)
    for start in range(0, total, batch_size):
        batch = tickers[start:start + batch_size]
        with ThreadPoolExecutor(max_workers=min(max_workers, len(batch))) as ex:
            futures = {ex.submit(_process_one, t, benchmark_df, price_range, min_dollar_vol,
                                  exclude_broken_out, exclude_downtrend, require_stage2,
                                  rsi_range, rvol_min, atr_pct_range): t for t in batch}
            for fut in as_completed(futures):
                t = futures[fut]
                try:
                    row_or_none, detail_or_none, err = fut.result()
                    if err:
                        # map error strings to counters
                        if err == "low_liquidity":
                            skipped_liquidity.append(t)
                        elif err.startswith("error:"):
                            errors.append(f"{t}: {err}")
                            results.append(row_or_none) if row_or_none else None
                        elif err in filtered_reasons:
                            filtered_reasons[err] += 1
                        else:
                            errors.append(f"{t}: {err}")
                    else:
                        if row_or_none is None and detail_or_none is None:
                            # skipped for a filtering reason already counted above
                            continue
                        if row_or_none is not None:
                            results.append(row_or_none)
                        if detail_or_none:
                            details[t] = detail_or_none
                except Exception as e:
                    errors.append(f"{t}: exception in future {e}")
        # small sleep between batches to lower rate of requests
        time.sleep(batch_sleep)

    meta = {
        "filtered_reasons": filtered_reasons,
        "skipped_liquidity": skipped_liquidity,
        "errors": errors,
        "no_data_count": no_data_count,
        "total": total,
    }
    return results, details, meta
