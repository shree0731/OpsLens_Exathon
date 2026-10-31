"""
OpsLens Fault Injector CLI
Usage: python -m data_generator.faults <name>

Available faults (touching ONLY OPSLENS tables):
- late_load
- row_drop (40%)
- schema_change
- duplicates
- revenue_mismatch (ORDERS vs LINEITEM totals)
- stale_feed (energy/weather latest timestamps stop advancing)
- job_failure
- reset (reload from source schemas and clear faults)

Each fault records a log entry in OPSLENS.FAULT_LOG.
"""

import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple
from backend.db import get_connection
from data_generator.setup_data import setup_opslens_schema
from data_generator.metadata_generator import generate_check_results_and_alerts, generate_trust_scores_and_baselines


def _log_fault(conn, fault_name: str, target_table: str, details: str, status: str = "ACTIVE"):
    """Inserts a record into OPSLENS.FAULT_LOG."""
    fault_id = f"flt_{uuid.uuid4().hex[:12]}"
    conn.execute(
        f"""
        INSERT INTO OPSLENS.FAULT_LOG (FAULT_ID, FAULT_NAME, TARGET_TABLE, DETAILS, STATUS, INJECTED_AT)
        VALUES ('{fault_id}', '{fault_name}', '{target_table}', '{details.replace("'", "''")}', '{status}', CURRENT_TIMESTAMP)
        """
    )
    return fault_id


def fault_late_load(conn) -> Dict[str, Any]:
    """Injects a late load fault into OPSLENS.PIPELINE_RUN_LOG and alerts."""
    print("\n[FAULT INJECTOR] >> Injecting: late_load...")
    
    # 1. Update the latest run log for load_orders
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

    # 2. Add Alert
    alert_id = f"alt_{uuid.uuid4().hex[:10]}"
    conn.execute(f"""
        INSERT INTO OPSLENS.ALERTS (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, STATUS, TRIGGERED_AT, IS_SIMULATED)
        VALUES ('{alert_id}', 'LATE_LOAD', 'HIGH', 'OPSLENS.ORDERS', 
                'Pipeline load_orders delayed by 240 mins', 
                'Batch order ingestion missed nightly 01:00 SLA. Started at 05:00 (+4 hours).',
                'TRIGGERED', CURRENT_TIMESTAMP, TRUE)
    """)

    # 3. Degrade Trust Score
    conn.execute("""
        UPDATE OPSLENS.TRUST_SCORES
        SET FRESHNESS_SCORE = 55.0, TRUST_SCORE = 71.5, STATUS = 'DEGRADED'
        WHERE OBJECT_NAME = 'OPSLENS.ORDERS'
    """)

    details = "Delayed latest load_orders start time by 4 hours, duration increased to 680s, alert triggered, trust score degraded."
    _log_fault(conn, "late_load", "OPSLENS.ORDERS", details)
    print("  >> [OK] Fault 'late_load' injected successfully.")
    return {"fault": "late_load", "target": "OPSLENS.ORDERS", "status": "INJECTED", "details": details}


def fault_row_drop(conn) -> Dict[str, Any]:
    """Deletes exactly 40% of rows from OPSLENS.ORDERS."""
    print("\n[FAULT INJECTOR] >> Injecting: row_drop (40%)...")
    before_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.ORDERS").fetchall()[0][0]

    # Drop 40% (MOD 5 is 0 or 1)
    conn.execute("DELETE FROM OPSLENS.ORDERS WHERE MOD(O_ORDERKEY, 5) IN (0, 1)")

    after_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.ORDERS").fetchall()[0][0]
    dropped = before_cnt - after_cnt
    pct_dropped = round((dropped / before_cnt) * 100, 2) if before_cnt else 0

    # Add Alert
    alert_id = f"alt_{uuid.uuid4().hex[:10]}"
    conn.execute(f"""
        INSERT INTO OPSLENS.ALERTS (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, STATUS, TRIGGERED_AT, IS_SIMULATED)
        VALUES ('{alert_id}', 'ROW_DROP', 'CRITICAL', 'OPSLENS.ORDERS',
                'Critical Volume Drop: 40% of rows missing',
                'Row count plummeted from {before_cnt:,} to {after_cnt:,} (-{pct_dropped}%). Severe upstream data loss suspected.',
                'TRIGGERED', CURRENT_TIMESTAMP, TRUE)
    """)

    # Update Check Results
    conn.execute(f"""
        UPDATE OPSLENS.CHECK_RESULTS
        SET STATUS = 'FAILED',
            ACTUAL_VALUE = '{after_cnt:,} rows',
            MESSAGE = 'CRITICAL: Row count dropped by {pct_dropped}% (expected {before_cnt:,})'
        WHERE TABLE_NAME = 'OPSLENS.ORDERS' AND CHECK_TYPE = 'ROW_COUNT'
    """)

    # Degrade Trust Score
    conn.execute("""
        UPDATE OPSLENS.TRUST_SCORES
        SET QUALITY_SCORE = 35.0, RELIABILITY_SCORE = 40.0, TRUST_SCORE = 42.0, STATUS = 'AT_RISK'
        WHERE OBJECT_NAME = 'OPSLENS.ORDERS'
    """)

    details = f"Dropped {dropped:,} rows (-{pct_dropped}%) from OPSLENS.ORDERS ({before_cnt:,} -> {after_cnt:,})."
    _log_fault(conn, "row_drop", "OPSLENS.ORDERS", details)
    print(f"  >> [OK] Before: {before_cnt:,} | After: {after_cnt:,} | Dropped: {dropped:,} ({pct_dropped}%)")
    return {"fault": "row_drop", "before": before_cnt, "after": after_cnt, "dropped": dropped, "pct": pct_dropped}


def fault_schema_change(conn) -> Dict[str, Any]:
    """Alters OPSLENS.ORDERS by adding an unexpected column."""
    print("\n[FAULT INJECTOR] >> Injecting: schema_change...")
    
    # Check if column already exists
    cols = [r[0] for r in conn.execute("SELECT COLUMN_NAME FROM SYS.EXA_ALL_COLUMNS WHERE COLUMN_SCHEMA='OPSLENS' AND COLUMN_TABLE='ORDERS'").fetchall()]
    col_name = "UNEXPECTED_TAX_SURCHARGE"
    if col_name not in cols:
        conn.execute(f"ALTER TABLE OPSLENS.ORDERS ADD COLUMN {col_name} DECIMAL(12,2) DEFAULT 0.00")
        action = f"Added column {col_name} DECIMAL(12,2)"
    else:
        action = f"Column {col_name} already exists"

    # Add Alert
    alert_id = f"alt_{uuid.uuid4().hex[:10]}"
    conn.execute(f"""
        INSERT INTO OPSLENS.ALERTS (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, STATUS, TRIGGERED_AT, IS_SIMULATED)
        VALUES ('{alert_id}', 'SCHEMA_DRIFT', 'HIGH', 'OPSLENS.ORDERS',
                'Unannounced Schema Mutation detected',
                'Unexpected column {col_name} added without migration plan approval.',
                'TRIGGERED', CURRENT_TIMESTAMP, TRUE)
    """)

    # Update Check Results
    conn.execute(f"""
        UPDATE OPSLENS.CHECK_RESULTS
        SET STATUS = 'FAILED',
            ACTUAL_VALUE = '10 columns (found {col_name})',
            MESSAGE = 'Schema validation failed: unexpected extra column {col_name}'
        WHERE TABLE_NAME = 'OPSLENS.ORDERS' AND CHECK_TYPE = 'SCHEMA_CHECK'
    """)

    details = f"Schema drifted on OPSLENS.ORDERS: {action}."
    _log_fault(conn, "schema_change", "OPSLENS.ORDERS", details)
    print(f"  >> [OK] {action}")
    return {"fault": "schema_change", "column_added": col_name, "status": "INJECTED"}


def fault_duplicates(conn) -> Dict[str, Any]:
    """Inserts duplicate rows into OPSLENS.LINEITEM."""
    print("\n[FAULT INJECTOR] >> Injecting: duplicates...")
    before_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.LINEITEM").fetchall()[0][0]

    # Re-insert existing records for order keys <= 1000
    conn.execute("INSERT INTO OPSLENS.LINEITEM SELECT * FROM OPSLENS.LINEITEM WHERE L_ORDERKEY <= 1000")

    after_cnt = conn.execute("SELECT COUNT(*) FROM OPSLENS.LINEITEM").fetchall()[0][0]
    inserted_dups = after_cnt - before_cnt

    # Add Alert
    alert_id = f"alt_{uuid.uuid4().hex[:10]}"
    conn.execute(f"""
        INSERT INTO OPSLENS.ALERTS (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, STATUS, TRIGGERED_AT, IS_SIMULATED)
        VALUES ('{alert_id}', 'DUPLICATES', 'CRITICAL', 'OPSLENS.LINEITEM',
                'Duplicate Lineitem primary records detected',
                'Detected {inserted_dups:,} duplicate rows for Order keys <= 1000. Double counting risk in revenue reporting.',
                'TRIGGERED', CURRENT_TIMESTAMP, TRUE)
    """)

    details = f"Injected {inserted_dups:,} duplicate records into OPSLENS.LINEITEM ({before_cnt:,} -> {after_cnt:,})."
    _log_fault(conn, "duplicates", "OPSLENS.LINEITEM", details)
    print(f"  >> [OK] Before: {before_cnt:,} | After: {after_cnt:,} | Duplicates added: {inserted_dups:,}")
    return {"fault": "duplicates", "before": before_cnt, "after": after_cnt, "added": inserted_dups}


def fault_revenue_mismatch(conn) -> Dict[str, Any]:
    """Mutates orders total price to cause a discrepancy with lineitems."""
    print("\n[FAULT INJECTOR] >> Injecting: revenue_mismatch...")
    
    # Calculate baseline sums
    q_orders = "SELECT SUM(O_TOTALPRICE) FROM OPSLENS.ORDERS"
    q_items = "SELECT SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT) * (1 + L_TAX)) FROM OPSLENS.LINEITEM"
    sum_orders_before = float(conn.execute(q_orders).fetchall()[0][0] or 0)
    sum_items_before = float(conn.execute(q_items).fetchall()[0][0] or 0)
    delta_before = round(abs(sum_orders_before - sum_items_before), 2)

    # Corrupt total price on 33% of orders
    conn.execute("UPDATE OPSLENS.ORDERS SET O_TOTALPRICE = O_TOTALPRICE * 1.35 WHERE MOD(O_ORDERKEY, 3) = 0")

    sum_orders_after = float(conn.execute(q_orders).fetchall()[0][0] or 0)
    delta_after = round(abs(sum_orders_after - sum_items_before), 2)

    # Add Alert
    alert_id = f"alt_{uuid.uuid4().hex[:10]}"
    conn.execute(f"""
        INSERT INTO OPSLENS.ALERTS (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, STATUS, TRIGGERED_AT, IS_SIMULATED)
        VALUES ('{alert_id}', 'REVENUE_MISMATCH', 'CRITICAL', 'OPSLENS.ORDERS',
                'Financial Reconciliation Discrepancy: ${delta_after:,.2f}',
                'Summed Orders total (${sum_orders_after:,.2f}) does not match Lineitem items net total (${sum_items_before:,.2f}). Delta = ${delta_after:,.2f}.',
                'TRIGGERED', CURRENT_TIMESTAMP, TRUE)
    """)

    # Update Check Results
    conn.execute(f"""
        UPDATE OPSLENS.CHECK_RESULTS
        SET STATUS = 'FAILED',
            ACTUAL_VALUE = 'Delta: ${delta_after:,.2f}',
            MESSAGE = 'CRITICAL Reconciliation failure: Orders exceed Lineitems by ${delta_after:,.2f}'
        WHERE TABLE_NAME = 'OPSLENS.ORDERS' AND CHECK_TYPE = 'RECONCILIATION'
    """)

    details = f"Corrupted order prices by +35% on MOD 3. Reconciliation delta grew from ${delta_before:,.2f} to ${delta_after:,.2f}."
    _log_fault(conn, "revenue_mismatch", "OPSLENS.ORDERS", details)
    print(f"  >> [OK] Delta Before: ${delta_before:,.2f} | Delta After: ${delta_after:,.2f}")
    return {"fault": "revenue_mismatch", "delta_before": delta_before, "delta_after": delta_after}


def fault_stale_feed(conn) -> Dict[str, Any]:
    """Deletes recent 14 days of energy readings and weather to freeze feed timestamps."""
    print("\n[FAULT INJECTOR] >> Injecting: stale_feed...")
    
    # Energy readings
    max_ts_before = conn.execute("SELECT MAX(READING_TS) FROM OPSLENS.ENERGY_READINGS").fetchall()[0][0]
    conn.execute("DELETE FROM OPSLENS.ENERGY_READINGS WHERE READING_TS >= TIMESTAMP '2025-03-18 00:00:00'")
    max_ts_after = conn.execute("SELECT MAX(READING_TS) FROM OPSLENS.ENERGY_READINGS").fetchall()[0][0]

    # Weather daily
    max_w_before = conn.execute("SELECT MAX(W_DATE) FROM OPSLENS.WEATHER_DAILY").fetchall()[0][0]
    conn.execute("DELETE FROM OPSLENS.WEATHER_DAILY WHERE W_DATE >= DATE '2025-12-18'")
    max_w_after = conn.execute("SELECT MAX(W_DATE) FROM OPSLENS.WEATHER_DAILY").fetchall()[0][0]

    # Add Alert
    alert_id = f"alt_{uuid.uuid4().hex[:10]}"
    conn.execute(f"""
        INSERT INTO OPSLENS.ALERTS (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, STATUS, TRIGGERED_AT, IS_SIMULATED)
        VALUES ('{alert_id}', 'STALE_FEED', 'HIGH', 'OPSLENS.ENERGY_READINGS',
                'IoT Telemetry Feed Frozen (Stale Data)',
                'Latest smart meter telemetry stopped at {max_ts_after}. No new readings ingested for 14 simulated days.',
                'TRIGGERED', CURRENT_TIMESTAMP, TRUE)
    """)

    # Update Check Results
    conn.execute(f"""
        UPDATE OPSLENS.CHECK_RESULTS
        SET STATUS = 'FAILED',
            ACTUAL_VALUE = 'Lag: 14 days',
            MESSAGE = 'CRITICAL: Feed freshness SLA breached. Latest reading: {max_ts_after}'
        WHERE TABLE_NAME = 'OPSLENS.ENERGY_READINGS' AND CHECK_TYPE = 'FRESHNESS'
    """)

    details = f"Cut 14 days of telemetry. Energy max ts: {max_ts_before} -> {max_ts_after}; Weather max: {max_w_before} -> {max_w_after}."
    _log_fault(conn, "stale_feed", "OPSLENS.ENERGY_READINGS", details)
    print(f"  >> [OK] Energy Max TS: {max_ts_before} -> {max_ts_after}")
    print(f"  >> [OK] Weather Max Date: {max_w_before} -> {max_w_after}")
    return {"fault": "stale_feed", "energy_before": str(max_ts_before), "energy_after": str(max_ts_after)}


def fault_job_failure(conn) -> Dict[str, Any]:
    """Injects a simulated pipeline job failure with an OOM error."""
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

    # Add Alert
    alert_id = f"alt_{uuid.uuid4().hex[:10]}"
    conn.execute(f"""
        INSERT INTO OPSLENS.ALERTS (ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, STATUS, TRIGGERED_AT, IS_SIMULATED)
        VALUES ('{alert_id}', 'JOB_FAILURE', 'CRITICAL', 'OPSLENS.REVENUE_MART',
                'Job build_revenue_mart FAILED (OOM Error)',
                'Transform stage aborted with OutOfMemoryException on hash join. Dependent dashboards unrefreshed.',
                'TRIGGERED', CURRENT_TIMESTAMP, TRUE)
    """)

    # Update Trust Score
    conn.execute("""
        UPDATE OPSLENS.TRUST_SCORES
        SET RELIABILITY_SCORE = 30.0, TRUST_SCORE = 45.0, STATUS = 'AT_RISK'
        WHERE OBJECT_NAME = 'OPSLENS.REVENUE_MART'
    """)

    details = "Inserted failed job run for build_revenue_mart (OutOfMemoryException), alert generated, trust score reduced to 45%."
    _log_fault(conn, "job_failure", "OPSLENS.REVENUE_MART", details)
    print("  >> [OK] Fault 'job_failure' injected successfully.")
    return {"fault": "job_failure", "job_id": "build_revenue_mart", "status": "FAILED"}


def fault_reset(conn) -> Dict[str, Any]:
    """
    Reloads all production tables from source schemas (TPCH, ENERGY, WEATHER),
    cleans up extra columns/duplicates, clears active faults, and restores baselines.
    """
    print("\n[FAULT INJECTOR] >> Executing: reset (Reloading all tables & clearing faults)...")
    
    # 1. Reload production tables from clean sample schemas
    reloaded_counts = setup_opslens_schema(force_reload=True)

    # 2. Mark active faults as CLEARED in FAULT_LOG
    conn.execute("""
        UPDATE OPSLENS.FAULT_LOG
        SET STATUS = 'CLEARED', CLEARED_AT = CURRENT_TIMESTAMP
        WHERE STATUS = 'ACTIVE'
    """)

    # 3. Regenerate clean checks, alerts, trust scores
    generate_check_results_and_alerts(conn)
    generate_trust_scores_and_baselines(conn)

    # 4. Log the reset action itself
    details = "Full reset executed: all production tables reloaded from source schemas, schema drift reverted, all faults marked CLEARED."
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
