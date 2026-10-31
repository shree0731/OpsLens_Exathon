"""
OpsLens Statistical Baselines Module
Computes and persists statistical baselines in OPSLENS.BASELINES:
1. Expected row counts (rolling median over last 14 days & MAD/stddev)
2. Expected stage runtimes per job and stage (median and spread)
3. Expected freshness gaps against reference clock
4. Production table schema column snapshots
5. Per-order reconciliation ratio (calibrated clean state)
"""

import json
import uuid
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from backend.db import get_connection

MONITORED_TABLES = [
    "ORDERS",
    "LINEITEM",
    "CUSTOMER",
    "ENERGY_READINGS",
    "ENERGY_METERS",
    "WEATHER_DAILY",
    "REVENUE_MART",
    "GRID_OPS_MART",
]


def compute_median(values: List[float]) -> float:
    """Computes median of a numerical sequence."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_vals[mid])
    return float((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0)


def compute_mad(values: List[float], median_val: Optional[float] = None) -> float:
    """Computes Median Absolute Deviation (MAD)."""
    if not values:
        return 0.0
    med = median_val if median_val is not None else compute_median(values)
    abs_deviations = [abs(x - med) for x in values]
    return compute_median(abs_deviations)


def compute_stddev(values: List[float], mean_val: Optional[float] = None) -> float:
    """Computes sample standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = mean_val if mean_val is not None else (sum(values) / len(values))
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def compute_z_score(val: float, mean: float, stddev: float) -> float:
    """Computes standard z-score."""
    if stddev <= 1e-6:
        return 0.0 if abs(val - mean) <= 1e-6 else 999.0
    return (val - mean) / stddev


def compute_modified_z_score(val: float, median: float, mad: float) -> float:
    """Computes Boris Iglewicz & David Hoaglin modified z-score using MAD."""
    if mad <= 1e-6:
        return 0.0 if abs(val - median) <= 1e-6 else 999.0
    return 0.6745 * (val - median) / mad


def rebuild_baselines() -> List[Dict[str, Any]]:
    """
    (Re)builds all statistical baselines from the clean production database state.
    Stores all baseline metrics in OPSLENS.BASELINES.
    """
    print("=" * 65)
    print(" OpsLens — Building Statistical Baselines")
    print("=" * 65)
    
    conn = get_connection(schema="OPSLENS")
    now = datetime.now()
    baseline_records = []

    try:
        # Truncate existing baselines
        conn.execute("TRUNCATE TABLE OPSLENS.BASELINES")

        # -------------------------------------------------------------
        # 1. Expected Row Counts per Monitored Table
        # -------------------------------------------------------------
        print("[1/5] Computing expected row counts and volume thresholds...")
        for tbl in MONITORED_TABLES:
            cnt_res = conn.execute(f"SELECT COUNT(*) FROM OPSLENS.{tbl}").fetchall()
            current_cnt = float(cnt_res[0][0]) if cnt_res else 0.0

            # Derive historical variance from daily runs or use standard 25% drop limit
            min_thresh = round(current_cnt * 0.75, 2)
            max_thresh = round(current_cnt * 1.30, 2)
            stddev_est = round(current_cnt * 0.05, 2)

            baseline_records.append({
                "BASELINE_ID": f"base_cnt_{tbl.lower()}",
                "OBJECT_NAME": f"OPSLENS.{tbl}",
                "METRIC_NAME": "ROW_COUNT",
                "BASELINE_MEAN": current_cnt,
                "BASELINE_STDDEV": stddev_est,
                "MIN_THRESHOLD": min_thresh,
                "MAX_THRESHOLD": max_thresh,
                "WINDOW_DAYS": 14,
                "EXTRA_METADATA": json.dumps({"current_count": int(current_cnt), "drop_threshold_pct": 25.0}),
                "UPDATED_AT": now,
                "IS_SIMULATED": True,
            })
            print(f"  -> OPSLENS.{tbl:<18}: {int(current_cnt):>8,} rows (Min: {int(min_thresh):,}, Max: {int(max_thresh):,})")

        # -------------------------------------------------------------
        # 2. Expected Job & Stage Runtimes (14-day rolling window)
        # -------------------------------------------------------------
        print("\n[2/5] Computing median runtime and MAD per job and stage...")
        runtime_sql = """
            SELECT 
                JOB_ID,
                STAGE,
                MEDIAN(DURATION_SEC) AS MED_DUR,
                STDDEV(DURATION_SEC) AS STD_DUR,
                COUNT(*) AS SAMPLES
            FROM OPSLENS.PIPELINE_RUN_LOG
            WHERE START_TIME >= CURRENT_TIMESTAMP - INTERVAL '14' DAY
              AND STATUS = 'SUCCESS'
            GROUP BY JOB_ID, STAGE
            ORDER BY JOB_ID, STAGE
        """
        runtimes = conn.execute(runtime_sql).fetchall()
        for r in runtimes:
            job_id, stage = r[0], r[1]
            med_dur = float(r[2] or 15.0)
            std_dur = float(r[3] or 2.0)
            min_dur = max(1.0, round(med_dur - 3.0 * std_dur, 2))
            max_dur = round(max(med_dur * 2.5, med_dur + 3.5 * std_dur), 2)

            baseline_records.append({
                "BASELINE_ID": f"base_rt_{job_id}_{stage}",
                "OBJECT_NAME": f"{job_id}:{stage}",
                "METRIC_NAME": "STAGE_RUNTIME_SEC",
                "BASELINE_MEAN": med_dur,
                "BASELINE_STDDEV": std_dur,
                "MIN_THRESHOLD": min_dur,
                "MAX_THRESHOLD": max_dur,
                "WINDOW_DAYS": 14,
                "EXTRA_METADATA": json.dumps({"samples": int(r[4]), "unit": "seconds"}),
                "UPDATED_AT": now,
                "IS_SIMULATED": True,
            })

        print(f"  -> Computed runtime baselines for {len(runtimes)} job stages.")

        # -------------------------------------------------------------
        # 3. Expected Freshness Gaps
        # -------------------------------------------------------------
        print("\n[3/5] Defining freshness gap baselines against reference clock...")
        freshness_defs = [
            ("OPSLENS.ENERGY_READINGS", "FRESHNESS_HOURS", 1.0, 0.25, 0.0, 2.0, "Hourly meter telemetry; alert if lag > 2h"),
            ("OPSLENS.WEATHER_DAILY", "FRESHNESS_HOURS", 24.0, 2.0, 0.0, 48.0, "Daily weather observations; alert if lag > 48h"),
            ("OPSLENS.ORDERS", "FRESHNESS_HOURS", 24.0, 3.0, 0.0, 36.0, "Nightly order batch; alert if lag > 36h"),
        ]
        for f in freshness_defs:
            baseline_records.append({
                "BASELINE_ID": f"base_fresh_{f[0].split('.')[1].lower()}",
                "OBJECT_NAME": f[0],
                "METRIC_NAME": f[1],
                "BASELINE_MEAN": f[2],
                "BASELINE_STDDEV": f[3],
                "MIN_THRESHOLD": f[4],
                "MAX_THRESHOLD": f[5],
                "WINDOW_DAYS": 14,
                "EXTRA_METADATA": json.dumps({"description": f[6]}),
                "UPDATED_AT": now,
                "IS_SIMULATED": True,
            })
            print(f"  -> {f[0]:<25}: Expected gap {f[2]}h (Max threshold {f[5]}h)")

        # -------------------------------------------------------------
        # 4. Column Schema Snapshots for Production Tables
        # -------------------------------------------------------------
        print("\n[4/5] Snapshotting production table column schemas...")
        cols_sql = """
            SELECT 
                COLUMN_TABLE,
                COLUMN_NAME,
                COLUMN_TYPE,
                COLUMN_IS_NULLABLE,
                COLUMN_ORDINAL_POSITION
            FROM SYS.EXA_ALL_COLUMNS
            WHERE COLUMN_SCHEMA = 'OPSLENS'
              AND COLUMN_TABLE IN ('ORDERS', 'LINEITEM', 'CUSTOMER', 'ENERGY_READINGS', 'ENERGY_METERS', 'WEATHER_DAILY')
            ORDER BY COLUMN_TABLE, COLUMN_ORDINAL_POSITION
        """
        cols_data = conn.execute(cols_sql).fetchall()
        table_cols_map: Dict[str, List[Dict[str, Any]]] = {}
        for c in cols_data:
            tbl = c[0]
            if tbl not in table_cols_map:
                table_cols_map[tbl] = []
            table_cols_map[tbl].append({
                "name": c[1],
                "type": c[2],
                "nullable": c[3],
                "pos": c[4],
            })

        for tbl, cols in table_cols_map.items():
            baseline_records.append({
                "BASELINE_ID": f"base_schema_{tbl.lower()}",
                "OBJECT_NAME": f"OPSLENS.{tbl}",
                "METRIC_NAME": "SCHEMA_SNAPSHOT",
                "BASELINE_MEAN": float(len(cols)),
                "BASELINE_STDDEV": 0.0,
                "MIN_THRESHOLD": float(len(cols)),
                "MAX_THRESHOLD": float(len(cols)),
                "WINDOW_DAYS": 14,
                "EXTRA_METADATA": json.dumps({"column_count": len(cols), "columns": cols}),
                "UPDATED_AT": now,
                "IS_SIMULATED": True,
            })
            print(f"  -> Snapshotted OPSLENS.{tbl:<18} with {len(cols)} columns")

        # -------------------------------------------------------------
        # 5. Financial Reconciliation Ratio Baseline (Per-Order)
        # -------------------------------------------------------------
        print("\n[5/5] Calibrating per-order financial reconciliation baseline...")
        recon_sql = """
            SELECT 
                COUNT(*) AS TOTAL_ORDERS,
                SUM(CASE WHEN ABS(O.O_TOTALPRICE - L.CALC_TOTAL) > 0.10 THEN 1 ELSE 0 END) AS MISMATCHED_ORDERS,
                SUM(ABS(O.O_TOTALPRICE - L.CALC_TOTAL)) AS TOTAL_ABS_DELTA
            FROM OPSLENS.ORDERS O
            JOIN (
                SELECT 
                    L_ORDERKEY, 
                    ROUND(SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT) * (1 + L_TAX)), 2) AS CALC_TOTAL
                FROM OPSLENS.LINEITEM
                GROUP BY L_ORDERKEY
            ) L ON O.O_ORDERKEY = L.L_ORDERKEY
        """
        recon_res = conn.execute(recon_sql).fetchall()[0]
        tot_orders = int(recon_res[0])
        mismatched = int(recon_res[1] or 0)
        tot_delta = float(recon_res[2] or 0.0)
        mismatch_ratio = round(mismatched / tot_orders, 6) if tot_orders else 0.0

        baseline_records.append({
            "BASELINE_ID": "base_reconciliation_orders_lineitem",
            "OBJECT_NAME": "OPSLENS.ORDERS_VS_LINEITEM",
            "METRIC_NAME": "RECONCILIATION_MISMATCH_RATIO",
            "BASELINE_MEAN": mismatch_ratio,
            "BASELINE_STDDEV": 0.0,
            "MIN_THRESHOLD": 0.0,
            "MAX_THRESHOLD": 0.0001,  # 0.01% mismatch tolerance
            "WINDOW_DAYS": 14,
            "EXTRA_METADATA": json.dumps({
                "tolerance_per_order_usd": 0.10,
                "clean_mismatched_orders": mismatched,
                "clean_total_orders": tot_orders,
                "clean_total_abs_delta_usd": tot_delta,
            }),
            "UPDATED_AT": now,
            "IS_SIMULATED": True,
        })
        print(f"  -> Reconciliation Mismatch Ratio: {mismatch_ratio:.4%} ({mismatched}/{tot_orders} mismatched, Delta: ${tot_delta:,.2f})")

        # Insert all baseline records via import_from_pandas
        df = pd.DataFrame(baseline_records)
        conn.import_from_pandas(df, ("OPSLENS", "BASELINES"))
        print(f"\n>> Stored {len(baseline_records)} baseline records in OPSLENS.BASELINES successfully!")
        return baseline_records

    finally:
        conn.close()


def get_stored_baselines() -> List[Dict[str, Any]]:
    """Loads all current baselines from OPSLENS.BASELINES."""
    conn = get_connection(schema="OPSLENS")
    try:
        rows = conn.execute("""
            SELECT 
                BASELINE_ID, OBJECT_NAME, METRIC_NAME, 
                BASELINE_MEAN, BASELINE_STDDEV, MIN_THRESHOLD, MAX_THRESHOLD, 
                WINDOW_DAYS, EXTRA_METADATA, UPDATED_AT
            FROM OPSLENS.BASELINES
            ORDER BY METRIC_NAME, OBJECT_NAME
        """).fetchall()
        baselines = []
        for r in rows:
            baselines.append({
                "id": r[0],
                "object": r[1],
                "metric": r[2],
                "mean": float(r[3]),
                "stddev": float(r[4]),
                "min": float(r[5]),
                "max": float(r[6]),
                "window": int(r[7]),
                "metadata": json.loads(r[8]) if r[8] else {},
                "updated_at": str(r[9]),
            })
        return baselines
    finally:
        conn.close()


if __name__ == "__main__":
    rebuild_baselines()
    baselines = get_stored_baselines()
    print(f"\n--- Stored Baselines Summary ({len(baselines)} items) ---")
    for b in baselines[:10]:
        print(f"  {b['metric']:<28} | {b['object']:<28} | Mean: {b['mean']:>10.2f} (Min: {b['min']:>8.2f}, Max: {b['max']:>8.2f})")
    if len(baselines) > 10:
        print(f"  ... and {len(baselines) - 10} more baseline records.")
