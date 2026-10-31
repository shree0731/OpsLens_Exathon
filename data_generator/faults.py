"""
OpsLens Fault Injector CLI
Usage: python -m data_generator.faults <name>

DETECTION INTEGRITY:
Faults ONLY corrupt production data or PIPELINE_RUN_LOG and record an entry in OPSLENS.FAULT_LOG.
They NEVER write to ALERTS, CHECK_RESULTS, or TRUST_SCORES.
Those tables are populated strictly by the Sentinel and Trust engines detecting real anomalies.

Available faults (touching ONLY OPSLENS copies):
- late_load
- row_drop (40%)
- schema_change
- duplicates
- revenue_mismatch
- stale_feed
- job_failure
- reset
"""

import sys
import uuid
from datetime import datetime
from typing import Dict, Any
from backend.db import get_connection
from data_generator.setup_data import setup_opslens_schema


def _log_fault(conn, fault_name: str, target_table: str, details: str, status: str = "ACTIVE"):
    """Inserts an audit record into OPSLENS.FAULT_LOG."""
    fault_id = f"flt_{uuid.uuid4().hex[:12]}"
    conn.execute(
        f"""
        INSERT INTO OPSLENS.FAULT_LOG (FAULT_ID, FAULT_NAME, TARGET_TABLE, DETAILS, STATUS, INJECTED_AT)
        VALUES ('{fault_id}', '{fault_name}', '{target_table}', '{details.replace("'", "''")}', '{status}', CURRENT_TIMESTAMP)
        """
    )
    return fault_id


def fault_late_load(conn) -> Dict[str, Any]:
    """
    Simulates a late-running pipeline run.
    Modifies PIPELINE_RUN_LOG for latest run of load_orders:
    Shifts start_time +4 hours, duration to 680s, status to 'WARNING'.
    Writes ONLY to FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Injecting: late_load...")
    
    conn.execute("""
        UPDATE OPSLENS.PIPELINE_RUN_LOG
        SET START_TIME = START_TIME + INTERVAL '4' HOUR,
            END_TIME = END_TIME + INTERVAL '4' HOUR,
            DURATION_SEC = 680.50,
            STATUS = 'WARNING',
            ERROR_MESSAGE = 'LateLoadAlert: Upstream source sync delayed by 240 minutes. SLA breached.'
        WHERE JOB_ID = 'load_orders' 
          AND RUN_ID = (SELECT MAX(RUN_ID) FROM OPSLENS.PIPELINE_RUN_LOG WHERE JOB_ID = 'load_orders')
    """)

    details = "Delayed latest load_orders start time by 4 hours, duration increased to 680.5s, status WARNING."
    _log_fault(conn, "late_load", "OPSLENS.ORDERS", details)
    print("  >> [OK] Fault 'late_load' injected (data only).")
    return {"fault": "late_load", "target": "OPSLENS.ORDERS", "status": "INJECTED", "details": details}


def fault_row_drop(conn) -> Dict[str, Any]:
    """
    Deletes exactly 40% of rows from OPSLENS.ORDERS.
    Writes ONLY to FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Injecting: row_drop (40%)...")
    before_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.ORDERS").fetchall()[0][0]

    # Drop 40% (MOD 5 is 0 or 1)
    conn.execute("DELETE FROM OPSLENS.ORDERS WHERE MOD(O_ORDERKEY, 5) IN (0, 1)")

    after_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.ORDERS").fetchall()[0][0]
    dropped = before_cnt - after_cnt
    pct_dropped = round((dropped / before_cnt) * 100, 2) if before_cnt else 0

    details = f"Dropped {dropped:,} rows (-{pct_dropped}%) from OPSLENS.ORDERS ({before_cnt:,} -> {after_cnt:,})."
    _log_fault(conn, "row_drop", "OPSLENS.ORDERS", details)
    print(f"  >> [OK] Before: {before_cnt:,} | After: {after_cnt:,} | Dropped: {dropped:,} ({pct_dropped}%)")
    return {"fault": "row_drop", "before": before_cnt, "after": after_cnt, "dropped": dropped, "pct": pct_dropped}


def fault_schema_change(conn) -> Dict[str, Any]:
    """
    Alters OPSLENS.ORDERS by adding an unexpected column.
    Writes ONLY to FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Injecting: schema_change...")
    
    cols = [r[0] for r in conn.execute("SELECT COLUMN_NAME FROM SYS.EXA_ALL_COLUMNS WHERE COLUMN_SCHEMA='OPSLENS' AND COLUMN_TABLE='ORDERS'").fetchall()]
    col_name = "UNEXPECTED_TAX_SURCHARGE"
    if col_name not in cols:
        conn.execute(f"ALTER TABLE OPSLENS.ORDERS ADD COLUMN {col_name} DECIMAL(12,2) DEFAULT 0.00")
        action = f"Added column {col_name} DECIMAL(12,2)"
    else:
        action = f"Column {col_name} already exists"

    details = f"Schema drifted on OPSLENS.ORDERS: {action}."
    _log_fault(conn, "schema_change", "OPSLENS.ORDERS", details)
    print(f"  >> [OK] {action}")
    return {"fault": "schema_change", "column_added": col_name, "status": "INJECTED"}


def fault_duplicates(conn) -> Dict[str, Any]:
    """
    Inserts duplicate rows into OPSLENS.LINEITEM.
    Writes ONLY to FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Injecting: duplicates...")
    before_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.LINEITEM").fetchall()[0][0]

    conn.execute("INSERT INTO OPSLENS.LINEITEM SELECT * FROM OPSLENS.LINEITEM WHERE L_ORDERKEY <= 1000")

    after_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.LINEITEM").fetchall()[0][0]
    inserted_dups = after_cnt - before_cnt

    details = f"Injected {inserted_dups:,} duplicate records into OPSLENS.LINEITEM ({before_cnt:,} -> {after_cnt:,})."
    _log_fault(conn, "duplicates", "OPSLENS.LINEITEM", details)
    print(f"  >> [OK] Before: {before_cnt:,} | After: {after_cnt:,} | Duplicates added: {inserted_dups:,}")
    return {"fault": "duplicates", "before": before_cnt, "after": after_cnt, "added": inserted_dups}


def fault_revenue_mismatch(conn) -> Dict[str, Any]:
    """
    Mutates prices on 33% of orders in OPSLENS.ORDERS (* 1.35),
    visibly worsening per-order reconciliation against LINEITEM.
    Writes ONLY to FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Injecting: revenue_mismatch...")
    
    # Per-order reconciliation query
    recon_query = """
    SELECT 
        COUNT(*) as total_orders,
        SUM(CASE WHEN ABS(O.O_TOTALPRICE - L.CALC_TOTAL) > 0.10 THEN 1 ELSE 0 END) as mismatched_orders,
        SUM(ABS(O.O_TOTALPRICE - L.CALC_TOTAL)) as total_abs_delta
    FROM OPSLENS.ORDERS O
    JOIN (
        SELECT L_ORDERKEY, ROUND(SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT) * (1 + L_TAX)), 2) AS CALC_TOTAL
        FROM OPSLENS.LINEITEM
        GROUP BY L_ORDERKEY
    ) L ON O.O_ORDERKEY = L.L_ORDERKEY
    """
    res_before = conn.execute(recon_query).fetchall()[0]
    mism_before, delta_before = res_before[1], float(res_before[2] or 0)

    # Mutate 33% of orders
    conn.execute("UPDATE OPSLENS.ORDERS SET O_TOTALPRICE = O_TOTALPRICE * 1.35 WHERE MOD(O_ORDERKEY, 3) = 0")

    res_after = conn.execute(recon_query).fetchall()[0]
    mism_after, delta_after = res_after[1], float(res_after[2] or 0)

    details = f"Mutated prices by +35% on MOD 3. Mismatched orders jumped from {mism_before} to {mism_after}. Delta: ${delta_before:,.2f} -> ${delta_after:,.2f}."
    _log_fault(conn, "revenue_mismatch", "OPSLENS.ORDERS", details)
    print(f"  >> [OK] Mismatched Orders Before: {mism_before} | After: {mism_after} (Delta: ${delta_after:,.2f})")
    return {"fault": "revenue_mismatch", "mismatched_before": mism_before, "mismatched_after": mism_after, "delta_after": delta_after}


def fault_stale_feed(conn) -> Dict[str, Any]:
    """
    Deletes the most recent 14 days of telemetry from ENERGY_READINGS and WEATHER_DAILY.
    Writes ONLY to FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Injecting: stale_feed...")
    
    max_ts_before = conn.execute("SELECT MAX(READING_TS) FROM OPSLENS.ENERGY_READINGS").fetchall()[0][0]
    conn.execute("DELETE FROM OPSLENS.ENERGY_READINGS WHERE READING_TS >= TIMESTAMP '2025-03-18 00:00:00'")
    max_ts_after = conn.execute("SELECT MAX(READING_TS) FROM OPSLENS.ENERGY_READINGS").fetchall()[0][0]

    max_w_before = conn.execute("SELECT MAX(W_DATE) FROM OPSLENS.WEATHER_DAILY").fetchall()[0][0]
    conn.execute("DELETE FROM OPSLENS.WEATHER_DAILY WHERE W_DATE >= DATE '2025-12-18'")
    max_w_after = conn.execute("SELECT MAX(W_DATE) FROM OPSLENS.WEATHER_DAILY").fetchall()[0][0]

    details = f"Deleted 14 days of telemetry. Energy max: {max_ts_before} -> {max_ts_after}; Weather max: {max_w_before} -> {max_w_after}."
    _log_fault(conn, "stale_feed", "OPSLENS.ENERGY_READINGS", details)
    print(f"  >> [OK] Energy Max TS: {max_ts_before} -> {max_ts_after}")
    print(f"  >> [OK] Weather Max Date: {max_w_before} -> {max_w_after}")
    return {"fault": "stale_feed", "energy_before": str(max_ts_before), "energy_after": str(max_ts_after)}


def fault_job_failure(conn) -> Dict[str, Any]:
    """
    Inserts a simulated failed stage run in PIPELINE_RUN_LOG for build_revenue_mart.
    Writes ONLY to FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Injecting: job_failure...")
    run_id = f"run_err_{uuid.uuid4().hex[:8]}"
    batch_id = f"batch_{datetime.now().strftime('%Y%m%d')}"

    conn.execute(f"""
        INSERT INTO OPSLENS.PIPELINE_RUN_LOG 
        (RUN_ID, BATCH_ID, JOB_ID, STAGE, START_TIME, END_TIME, DURATION_SEC, STATUS, ROWS_LOADED, ERROR_MESSAGE, IS_SIMULATED)
        VALUES 
        ('{run_id}', '{batch_id}', 'build_revenue_mart', 'transform', 
         CURRENT_TIMESTAMP - INTERVAL '15' MINUTE, CURRENT_TIMESTAMP, 912.40, 'FAILED', 0,
         'OutOfMemoryException: Hash join spilled beyond persistent buffer quota (exceeded 4096 MB). Execution killed by ResourceManager.',
         TRUE)
    """)

    details = "Inserted failed stage transform in build_revenue_mart (OutOfMemoryException) into PIPELINE_RUN_LOG."
    _log_fault(conn, "job_failure", "OPSLENS.REVENUE_MART", details)
    print("  >> [OK] Fault 'job_failure' injected (run log only).")
    return {"fault": "job_failure", "job_id": "build_revenue_mart", "status": "FAILED"}


def fault_reset(conn) -> Dict[str, Any]:
    """
    Reloads all production tables from source schemas (TPCH, ENERGY, WEATHER),
    cleans up extra columns/duplicates, restores OPSLENS.CONFIG,
    and marks all active faults as CLEARED in FAULT_LOG.
    """
    print("\n[FAULT INJECTOR] >> Executing: reset (Reloading all tables & clearing faults)...")
    
    # 1. Reload production tables and reset config
    reloaded_counts = setup_opslens_schema(force_reload=True)

    # 2. Mark active faults as CLEARED in FAULT_LOG
    conn.execute("""
        UPDATE OPSLENS.FAULT_LOG
        SET STATUS = 'CLEARED', CLEARED_AT = CURRENT_TIMESTAMP
        WHERE STATUS = 'ACTIVE'
    """)

    details = "Full reset executed: all production tables reloaded from source schemas, config restored, active faults CLEARED."
    _log_fault(conn, "reset", "ALL_TABLES", details, status="CLEARED")

    print("  >> [OK] All production tables reloaded and faults cleared.")
    return {"fault": "reset", "reloaded_counts": reloaded_counts, "status": "CLEARED"}


FAULTS_MAP = {
    "late_load": fault_late_load,
    "row_drop": fault_row_drop,
    "schema_change": fault_schema_change,
    "duplicates": fault_duplicates,
    "revenue_mismatch": fault_revenue_mismatch,
    "stale_feed": fault_stale_feed,
    "job_failure": fault_job_failure,
    "reset": fault_reset,
}


def run_fault(fault_name: str) -> Dict[str, Any]:
    """Executes the given fault by name."""
    if fault_name not in FAULTS_MAP:
        raise ValueError(f"Unknown fault '{fault_name}'. Supported faults: {list(FAULTS_MAP.keys())}")

    conn = get_connection(schema="OPSLENS")
    try:
        return FAULTS_MAP[fault_name](conn)
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m data_generator.faults <fault_name>")
        print(f"Supported faults: {list(FAULTS_MAP.keys())}")
        sys.exit(1)

    name = sys.argv[1].lower().strip()
    try:
        res = run_fault(name)
        print(f"\nResult: {res}")
    except Exception as exc:
        print(f"\n[ERROR] Fault execution failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
