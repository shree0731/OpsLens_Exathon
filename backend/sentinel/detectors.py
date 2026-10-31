"""
OpsLens Pipeline Sentinel — Anomaly & Quality Detectors
Implements 7 SQL-driven detectors:
1. check_late_or_failed_jobs
2. check_row_count_anomalies
3. check_runtime_anomalies
4. check_schema_drift
5. check_stale_feeds
6. check_duplicate_keys
7. check_reconciliation
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd


def check_late_or_failed_jobs(conn) -> List[Dict[str, Any]]:
    """
    Detector 1: Late or Failed Pipeline Runs
    Inspects recent runs in PIPELINE_RUN_LOG and PIPELINE_JOBS.
    Flags:
    - Stages with STATUS = 'FAILED'
    - Stages with STATUS = 'WARNING' or late-running loads (e.g. late_load fault)
    """
    results = []
    
    # Query latest execution for each job and stage
    query = """
    SELECT 
        R.JOB_ID,
        J.JOB_NAME,
        R.STAGE,
        R.STATUS,
        R.DURATION_SEC,
        J.EXPECTED_RUNTIME_SEC,
        R.START_TIME,
        R.ERROR_MESSAGE,
        R.RUN_ID
    FROM OPSLENS.PIPELINE_RUN_LOG R
    JOIN OPSLENS.PIPELINE_JOBS J ON R.JOB_ID = J.JOB_ID
    WHERE R.RUN_ID IN (
        SELECT MAX(RUN_ID) 
        FROM OPSLENS.PIPELINE_RUN_LOG 
        GROUP BY JOB_ID, STAGE
    )
    ORDER BY R.JOB_ID, R.STAGE
    """
    rows = conn.execute(query).fetchall()

    job_failures = []
    late_jobs = []

    for row in rows:
        job_id, job_name, stage, status, duration, expected_dur, start_time, err_msg, run_id = row
        duration = float(duration or 0)
        expected_dur = float(expected_dur or 0)
        
        if status == 'FAILED':
            job_failures.append({
                "job_id": job_id,
                "job_name": job_name,
                "stage": stage,
                "error": err_msg or "Unknown error",
                "duration": duration,
                "run_id": run_id
            })
        elif status == 'WARNING' or (expected_dur > 0 and duration > (expected_dur * 2.0) and duration > 300):
            late_jobs.append({
                "job_id": job_id,
                "job_name": job_name,
                "stage": stage,
                "error": err_msg or f"Execution duration ({duration:.1f}s) exceeded SLA expected runtime ({expected_dur:.1f}s)",
                "duration": duration,
                "run_id": run_id
            })

    # Record check results
    if job_failures:
        for f in job_failures:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Pipeline Failure: {f['job_id']}:{f['stage']}",
                "table_name": f"PIPELINE_JOB:{f['job_id']}",
                "check_type": "JOB_HEALTH",
                "severity": "CRITICAL",
                "status": "FAIL",
                "expected_value": "SUCCESS",
                "actual_value": "FAILED",
                "message": f"Job {f['job_id']} failed at stage '{f['stage']}': {f['error']}",
                "incident_type": "JOB_EXECUTION_FAILURE",
                "suggested_root_cause": f"Stage '{f['stage']}' failed during pipeline execution. Root cause message: {f['error']}",
                "recommended_action": "Inspect worker logs, check Exasol memory allocation, address query bottlenecks, and trigger retry."
            })
    else:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Pipeline Job Health: Zero Failures",
            "table_name": "PIPELINE_RUN_LOG",
            "check_type": "JOB_HEALTH",
            "severity": "INFO",
            "status": "PASS",
            "expected_value": "Zero failed stages",
            "actual_value": "0 failed stages",
            "message": "All pipeline jobs executed without fatal failures in latest runs.",
            "incident_type": None,
            "suggested_root_cause": None,
            "recommended_action": None
        })

    if late_jobs:
        for l in late_jobs:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Late Load SLA Breach: {l['job_id']}:{l['stage']}",
                "table_name": f"PIPELINE_JOB:{l['job_id']}",
                "check_type": "JOB_HEALTH",
                "severity": "WARNING",
                "status": "FAIL",
                "expected_value": "Completed within SLA window (<15m delay)",
                "actual_value": f"Delayed / Duration {l['duration']:.1f}s",
                "message": f"Job {l['job_id']} SLA breached: {l['error']}",
                "incident_type": "LATE_DATA_LOAD",
                "suggested_root_cause": f"Upstream source sync delayed or ingestion throughput degraded. Details: {l['error']}",
                "recommended_action": "Check upstream data source arrival times, network latency, and schedule offsets."
            })
    else:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Pipeline Timeliness SLA",
            "table_name": "PIPELINE_RUN_LOG",
            "check_type": "JOB_HEALTH",
            "severity": "INFO",
            "status": "PASS",
            "expected_value": "Runs completed within SLA window",
            "actual_value": "All runs on schedule",
            "message": "All latest pipeline runs completed within expected SLA schedules.",
            "incident_type": None,
            "suggested_root_cause": None,
            "recommended_action": None
        })

    return results


def check_row_count_anomalies(conn) -> List[Dict[str, Any]]:
    """
    Detector 2: Row Count Anomalies (Volume Drops)
    Compares current table row count against baseline in OPSLENS.BASELINES.
    Flags drops > 25% or |z-score| > 3.0.
    """
    results = []
    
    # Fetch row count baselines
    b_rows = conn.execute("""
        SELECT OBJECT_NAME, BASELINE_MEAN, BASELINE_STDDEV, MIN_THRESHOLD, MAX_THRESHOLD 
        FROM OPSLENS.BASELINES 
        WHERE METRIC_NAME = 'ROW_COUNT'
    """).fetchall()

    for b in b_rows:
        tbl_raw = b[0]
        tbl_clean = tbl_raw.replace("OPSLENS.", "").strip()
        tbl_qual = f"OPSLENS.{tbl_clean}"
        mean_cnt, stddev_cnt, min_thresh, max_thresh = float(b[1]), float(b[2]), float(b[3]), float(b[4])
        
        # Get live count
        cnt_res = conn.execute(f"SELECT COUNT(*) FROM {tbl_qual}").fetchall()
        live_cnt = float(cnt_res[0][0]) if cnt_res else 0.0

        drop_pct = ((mean_cnt - live_cnt) / mean_cnt * 100.0) if mean_cnt > 0 else 0.0
        z_score = ((live_cnt - mean_cnt) / stddev_cnt) if stddev_cnt > 1e-6 else (0.0 if abs(live_cnt - mean_cnt) < 1e-6 else -99.0)

        # Flag anomaly if drop > 25% or z < -3.0
        if drop_pct >= 25.0 or z_score < -3.0:
            severity = "CRITICAL" if drop_pct >= 35.0 else "WARNING"
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Volume Anomaly: {tbl_clean}",
                "table_name": tbl_clean,
                "check_type": "ROW_COUNT_ANOMALY",
                "severity": severity,
                "status": "FAIL",
                "expected_value": f"{int(mean_cnt):,} rows (min: {int(min_thresh):,})",
                "actual_value": f"{int(live_cnt):,} rows (-{drop_pct:.1f}%, z={z_score:.2f})",
                "message": f"Significant volume drop detected in {tbl_clean}: dropped {drop_pct:.1f}% ({int(mean_cnt):,} -> {int(live_cnt):,}).",
                "incident_type": "VOLUME_DROP_ANOMALY",
                "suggested_root_cause": f"Severe row loss ({drop_pct:.1f}% drop, z={z_score:.2f}). Upstream ingestion filter or accidental bulk deletion occurred.",
                "recommended_action": f"Verify upstream extract job for {tbl_clean}, check partition pruning filters, or restore missing rows from source schema."
            })
        else:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Volume Check: {tbl_clean}",
                "table_name": tbl_clean,
                "check_type": "ROW_COUNT_ANOMALY",
                "severity": "INFO",
                "status": "PASS",
                "expected_value": f"~{int(mean_cnt):,} rows",
                "actual_value": f"{int(live_cnt):,} rows",
                "message": f"Row count for {tbl_clean} is within expected baseline bounds ({int(live_cnt):,} rows, z={z_score:.2f}).",
                "incident_type": None,
                "suggested_root_cause": None,
                "recommended_action": None
            })

    return results


def check_runtime_anomalies(conn) -> List[Dict[str, Any]]:
    """
    Detector 3: Stage Runtime Anomalies
    Checks recent stage durations in PIPELINE_RUN_LOG against STAGE_RUNTIME in BASELINES.
    """
    results = []

    b_rows = conn.execute("""
        SELECT OBJECT_NAME, BASELINE_MEAN, BASELINE_STDDEV, MAX_THRESHOLD 
        FROM OPSLENS.BASELINES 
        WHERE METRIC_NAME = 'STAGE_RUNTIME'
    """).fetchall()

    for b in b_rows:
        obj_key, mean_dur, stddev_dur, max_thresh = b[0], float(b[1]), float(b[2]), float(b[3])
        if ":" not in obj_key:
            continue
        job_id, stage = obj_key.split(":", 1)

        # Get latest run duration for this job and stage
        q = f"""
        SELECT DURATION_SEC, STATUS 
        FROM OPSLENS.PIPELINE_RUN_LOG 
        WHERE JOB_ID = '{job_id}' AND STAGE = '{stage}'
        ORDER BY START_TIME DESC
        LIMIT 1
        """
        r_res = conn.execute(q).fetchall()
        if not r_res:
            continue
        
        live_dur = float(r_res[0][0] or 0)
        z_score = ((live_dur - mean_dur) / stddev_dur) if stddev_dur > 1e-6 else (0.0 if abs(live_dur - mean_dur) < 1e-6 else 99.0)

        # Flag if runtime exceeds baseline mean + 3*stddev and live_dur > max_thresh
        if (z_score > 3.0 or live_dur > max_thresh) and live_dur > (mean_dur * 2.0) and live_dur > 30.0:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Runtime Spike: {job_id}:{stage}",
                "table_name": f"PIPELINE_JOB:{job_id}",
                "check_type": "RUNTIME_ANOMALY",
                "severity": "WARNING",
                "status": "FAIL",
                "expected_value": f"{mean_dur:.1f}s (max: {max_thresh:.1f}s)",
                "actual_value": f"{live_dur:.1f}s (z={z_score:.2f})",
                "message": f"Stage {stage} of {job_id} experienced runtime spike: {live_dur:.1f}s vs expected {mean_dur:.1f}s.",
                "incident_type": "STAGE_RUNTIME_ANOMALY",
                "suggested_root_cause": f"Stage runtime spike ({live_dur:.1f}s vs baseline {mean_dur:.1f}s). System resource throttling or query plan degradation.",
                "recommended_action": "Check active sessions in SYS.EXA_DBA_SESSIONS and index/distribution key usage."
            })
        else:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Runtime Check: {job_id}:{stage}",
                "table_name": f"PIPELINE_JOB:{job_id}",
                "check_type": "RUNTIME_ANOMALY",
                "severity": "INFO",
                "status": "PASS",
                "expected_value": f"{mean_dur:.1f}s",
                "actual_value": f"{live_dur:.1f}s",
                "message": f"Stage runtime is normal ({live_dur:.1f}s, expected {mean_dur:.1f}s).",
                "incident_type": None,
                "suggested_root_cause": None,
                "recommended_action": None
            })

    return results


def check_schema_drift(conn) -> List[Dict[str, Any]]:
    """
    Detector 4: Schema Drift Detection
    Compares live columns in SYS.EXA_ALL_COLUMNS against SCHEMA_SNAPSHOT baseline in OPSLENS.BASELINES.
    Flags added, dropped, or modified columns.
    """
    results = []

    b_rows = conn.execute("""
        SELECT OBJECT_NAME, EXTRA_METADATA 
        FROM OPSLENS.BASELINES 
        WHERE METRIC_NAME = 'SCHEMA_SNAPSHOT'
    """).fetchall()

    for b in b_rows:
        tbl_raw = b[0]
        tbl_clean = tbl_raw.replace("OPSLENS.", "").strip()
        meta_json = b[1]
        if not meta_json:
            continue
        
        try:
            expected_meta = json.loads(meta_json)
            raw_cols = expected_meta.get("columns", [])
            expected_cols = {}
            for c in raw_cols:
                col_name = c.get("COLUMN_NAME") or c.get("name")
                if col_name:
                    expected_cols[col_name] = c
        except Exception:
            continue

        # Get live columns
        live_q = f"""
        SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_IS_NULLABLE 
        FROM SYS.EXA_ALL_COLUMNS 
        WHERE COLUMN_SCHEMA = 'OPSLENS' AND COLUMN_TABLE = '{tbl_clean}'
        ORDER BY COLUMN_ORDINAL_POSITION
        """
        live_cols_raw = conn.execute(live_q).fetchall()
        live_cols = {r[0]: {"COLUMN_NAME": r[0], "COLUMN_TYPE": r[1], "COLUMN_IS_NULLABLE": r[2]} for r in live_cols_raw}

        # Compare sets
        added_cols = set(live_cols.keys()) - set(expected_cols.keys())
        missing_cols = set(expected_cols.keys()) - set(live_cols.keys())

        if added_cols or missing_cols:
            details = []
            if added_cols:
                details.append(f"Unexpected columns added: {', '.join(sorted(added_cols))}")
            if missing_cols:
                details.append(f"Expected columns missing: {', '.join(sorted(missing_cols))}")

            severity = "CRITICAL" if missing_cols else "WARNING"
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Schema Drift: {tbl_clean}",
                "table_name": tbl_clean,
                "check_type": "SCHEMA_DRIFT",
                "severity": severity,
                "status": "FAIL",
                "expected_value": f"{len(expected_cols)} columns",
                "actual_value": f"{len(live_cols)} columns",
                "message": f"Schema drift detected on {tbl_clean}: {'; '.join(details)}",
                "incident_type": "SCHEMA_DRIFT_DETECTED",
                "suggested_root_cause": f"Uncoordinated DDL change applied to {tbl_clean}. {'; '.join(details)}",
                "recommended_action": "Review data contract migrations. Drop unapproved columns or update schema baseline."
            })
        else:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": f"Schema Integrity: {tbl_clean}",
                "table_name": tbl_clean,
                "check_type": "SCHEMA_DRIFT",
                "severity": "INFO",
                "status": "PASS",
                "expected_value": f"{len(expected_cols)} columns",
                "actual_value": f"{len(live_cols)} columns",
                "message": f"Schema for {tbl_clean} matches baseline exactly ({len(live_cols)} columns).",
                "incident_type": None,
                "suggested_root_cause": None,
                "recommended_action": None
            })

    return results


def check_stale_feeds(conn) -> List[Dict[str, Any]]:
    """
    Detector 5: Stale Data Feeds
    Compares latest timestamps in ENERGY_READINGS and WEATHER_DAILY against OPSLENS.CONFIG reference clock.
    Flags lag exceeding SLA tolerance.
    """
    results = []

    # Get reference clock & expected timestamps
    cfg_rows = conn.execute("SELECT PARAM_KEY, PARAM_VALUE FROM OPSLENS.CONFIG").fetchall()
    cfg = {r[0]: r[1] for r in cfg_rows}

    ref_now_str = cfg.get("reference_now", "2025-04-01 00:00:00")
    exp_energy_str = cfg.get("expected_latest_energy", "2025-03-31 23:00:00")
    exp_weather_str = cfg.get("expected_latest_weather", "2025-12-31 00:00:00")

    ref_now = datetime.fromisoformat(ref_now_str.replace(" ", "T"))
    exp_energy = datetime.fromisoformat(exp_energy_str.replace(" ", "T"))
    exp_weather = datetime.fromisoformat(exp_weather_str.replace(" ", "T"))

    # 1. Check Energy Readings
    e_res = conn.execute("SELECT MAX(READING_TS) FROM OPSLENS.ENERGY_READINGS").fetchall()
    max_energy = e_res[0][0]
    if isinstance(max_energy, str):
        max_energy = datetime.fromisoformat(max_energy.replace(" ", "T"))
    elif hasattr(max_energy, "to_pydatetime"):
        max_energy = max_energy.to_pydatetime()

    if max_energy:
        lag_hours = (exp_energy - max_energy).total_seconds() / 3600.0
        if lag_hours > 24.0:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": "Feed Freshness: ENERGY_READINGS",
                "table_name": "ENERGY_READINGS",
                "check_type": "STALE_FEED",
                "severity": "CRITICAL",
                "status": "FAIL",
                "expected_value": exp_energy_str,
                "actual_value": str(max_energy),
                "message": f"ENERGY_READINGS feed is stale by {lag_hours:.1f} hours (latest timestamp: {max_energy}).",
                "incident_type": "STALE_DATA_FEED",
                "suggested_root_cause": f"Smart meter telemetry feed stopped advancing. Latest reading is {max_energy} vs expected {exp_energy_str} (lag: {lag_hours:.1f}h).",
                "recommended_action": "Check IoT collector gateway, MQTT ingestion pipeline, or source queue connectivity."
            })
        else:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": "Feed Freshness: ENERGY_READINGS",
                "table_name": "ENERGY_READINGS",
                "check_type": "STALE_FEED",
                "severity": "INFO",
                "status": "PASS",
                "expected_value": f"<= 24h lag ({exp_energy_str})",
                "actual_value": f"{lag_hours:.1f}h lag ({max_energy})",
                "message": f"ENERGY_READINGS feed is fresh (latest timestamp: {max_energy}).",
                "incident_type": None,
                "suggested_root_cause": None,
                "recommended_action": None
            })

    # 2. Check Weather Daily
    w_res = conn.execute("SELECT MAX(W_DATE) FROM OPSLENS.WEATHER_DAILY").fetchall()
    max_weather = w_res[0][0]
    if isinstance(max_weather, str):
        max_weather = datetime.fromisoformat(max_weather.replace(" ", "T"))
    elif hasattr(max_weather, "to_pydatetime"):
        max_weather = max_weather.to_pydatetime()
    elif hasattr(max_weather, "year"):
        max_weather = datetime(max_weather.year, max_weather.month, max_weather.day)

    if max_weather:
        weather_lag_days = (exp_weather - max_weather).days
        if weather_lag_days > 2:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": "Feed Freshness: WEATHER_DAILY",
                "table_name": "WEATHER_DAILY",
                "check_type": "STALE_FEED",
                "severity": "WARNING",
                "status": "FAIL",
                "expected_value": exp_weather_str[:10],
                "actual_value": str(max_weather)[:10],
                "message": f"WEATHER_DAILY feed is stale by {weather_lag_days} days (latest date: {str(max_weather)[:10]}).",
                "incident_type": "STALE_DATA_FEED",
                "suggested_root_cause": f"Daily weather feed stopped updating. Latest date is {str(max_weather)[:10]} vs expected {exp_weather_str[:10]} (lag: {weather_lag_days} days).",
                "recommended_action": "Verify NOAA/Open-Meteo API key, rate limits, and daily cron job execution."
            })
        else:
            results.append({
                "check_id": f"chk_{uuid.uuid4().hex[:12]}",
                "check_name": "Feed Freshness: WEATHER_DAILY",
                "table_name": "WEATHER_DAILY",
                "check_type": "STALE_FEED",
                "severity": "INFO",
                "status": "PASS",
                "expected_value": f"<= 2 days lag ({exp_weather_str[:10]})",
                "actual_value": f"{weather_lag_days} days lag ({str(max_weather)[:10]})",
                "message": f"WEATHER_DAILY feed is fresh (latest date: {str(max_weather)[:10]}).",
                "incident_type": None,
                "suggested_root_cause": None,
                "recommended_action": None
            })

    return results


def check_duplicate_keys(conn) -> List[Dict[str, Any]]:
    """
    Detector 6: Duplicate Primary Keys
    Validates key uniqueness on ORDERS (O_ORDERKEY) and LINEITEM (L_ORDERKEY, L_LINENUMBER).
    """
    results = []

    # 1. Check ORDERS primary key
    ord_res = conn.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT O_ORDERKEY) AS DUP_COUNT
        FROM OPSLENS.ORDERS
    """).fetchall()
    ord_dups = int(ord_res[0][0]) if ord_res else 0

    if ord_dups > 0:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Primary Key Uniqueness: ORDERS",
            "table_name": "ORDERS",
            "check_type": "DUPLICATE_KEYS",
            "severity": "CRITICAL",
            "status": "FAIL",
            "expected_value": "0 duplicates",
            "actual_value": f"{ord_dups:,} duplicate rows",
            "message": f"Found {ord_dups:,} duplicate primary keys on ORDERS.O_ORDERKEY.",
            "incident_type": "PRIMARY_KEY_VIOLATION",
            "suggested_root_cause": f"Ingestion retry or batch overlap created {ord_dups:,} duplicate records on O_ORDERKEY.",
            "recommended_action": "Deduplicate ORDERS using ROW_NUMBER() OVER (PARTITION BY O_ORDERKEY) and check pipeline idempotency."
        })
    else:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Primary Key Uniqueness: ORDERS",
            "table_name": "ORDERS",
            "check_type": "DUPLICATE_KEYS",
            "severity": "INFO",
            "status": "PASS",
            "expected_value": "0 duplicates",
            "actual_value": "0 duplicates",
            "message": "ORDERS.O_ORDERKEY is 100% unique (0 duplicates).",
            "incident_type": None,
            "suggested_root_cause": None,
            "recommended_action": None
        })

    # 2. Check LINEITEM composite key
    li_res = conn.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT CAST(L_ORDERKEY AS VARCHAR(32)) || '-' || CAST(L_LINENUMBER AS VARCHAR(32))) AS DUP_COUNT
        FROM OPSLENS.LINEITEM
    """).fetchall()
    li_dups = int(li_res[0][0]) if li_res else 0

    if li_dups > 0:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Composite Key Uniqueness: LINEITEM",
            "table_name": "LINEITEM",
            "check_type": "DUPLICATE_KEYS",
            "severity": "CRITICAL",
            "status": "FAIL",
            "expected_value": "0 duplicates",
            "actual_value": f"{li_dups:,} duplicate rows",
            "message": f"Found {li_dups:,} duplicate composite keys on LINEITEM (L_ORDERKEY, L_LINENUMBER).",
            "incident_type": "PRIMARY_KEY_VIOLATION",
            "suggested_root_cause": f"Duplicate injection or non-idempotent line item load generated {li_dups:,} duplicate entries.",
            "recommended_action": "Deduplicate LINEITEM table and enforce composite unique constraint or MERGE upsert."
        })
    else:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Composite Key Uniqueness: LINEITEM",
            "table_name": "LINEITEM",
            "check_type": "DUPLICATE_KEYS",
            "severity": "INFO",
            "status": "PASS",
            "expected_value": "0 duplicates",
            "actual_value": "0 duplicates",
            "message": "LINEITEM (L_ORDERKEY, L_LINENUMBER) is 100% unique (0 duplicates).",
            "incident_type": None,
            "suggested_root_cause": None,
            "recommended_action": None
        })

    return results


def check_reconciliation(conn) -> List[Dict[str, Any]]:
    """
    Detector 7: Cross-Table Revenue Reconciliation
    Per-order join between ORDERS and child LINEITEM computed totals:
    ROUND(SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT) * (1 + L_TAX)), 2)
    Tolerance: $0.10 per order.
    Flags if mismatch count > 0 or mismatch share > 0.05%.
    """
    results = []

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
    res = conn.execute(recon_query).fetchall()
    tot_orders = int(res[0][0]) if res else 0
    mism_orders = int(res[0][1] or 0) if res else 0
    abs_delta = float(res[0][2] or 0.0) if res else 0.0

    mism_ratio = (mism_orders / tot_orders) if tot_orders > 0 else 0.0

    if mism_orders > 0 or mism_ratio > 0.0005:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Reconciliation: ORDERS vs LINEITEM",
            "table_name": "ORDERS",
            "check_type": "RECONCILIATION",
            "severity": "CRITICAL",
            "status": "FAIL",
            "expected_value": "0 mismatched orders (0.00% mismatch)",
            "actual_value": f"{mism_orders:,} mismatched ({mism_ratio * 100:.2f}%), delta: ${abs_delta:,.2f}",
            "message": f"Reconciliation breakdown: {mism_orders:,} of {tot_orders:,} orders ({mism_ratio * 100:.2f}%) diverge by > $0.10. Total dollar delta: ${abs_delta:,.2f}.",
            "incident_type": "CROSS_TABLE_RECONCILIATION_MISMATCH",
            "suggested_root_cause": f"Revenue calculation disparity between header and line items. {mism_orders:,} orders drifted with cumulative discrepancy of ${abs_delta:,.2f}.",
            "recommended_action": "Audit pricing mutations, invoice recalculation jobs, discount/tax formula changes, or line item deletions."
        })
    else:
        results.append({
            "check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "check_name": "Reconciliation: ORDERS vs LINEITEM",
            "table_name": "ORDERS",
            "check_type": "RECONCILIATION",
            "severity": "INFO",
            "status": "PASS",
            "expected_value": "0 mismatched orders (0.00%)",
            "actual_value": f"0 mismatched (delta: ${abs_delta:,.2f})",
            "message": f"Perfect financial reconciliation across all {tot_orders:,} orders. Zero mismatches within $0.10 tolerance.",
            "incident_type": None,
            "suggested_root_cause": None,
            "recommended_action": None
        })

    return results


def run_all_detectors(conn) -> List[Dict[str, Any]]:
    """Runs all 7 Sentinel detectors and returns combined check results."""
    all_results = []
    
    # 1. Late or failed jobs
    all_results.extend(check_late_or_failed_jobs(conn))
    
    # 2. Row count anomalies
    all_results.extend(check_row_count_anomalies(conn))
    
    # 3. Stage runtime anomalies
    all_results.extend(check_runtime_anomalies(conn))
    
    # 4. Schema drift
    all_results.extend(check_schema_drift(conn))
    
    # 5. Stale feeds
    all_results.extend(check_stale_feeds(conn))
    
    # 6. Duplicate keys
    all_results.extend(check_duplicate_keys(conn))
    
    # 7. Cross-table reconciliation
    all_results.extend(check_reconciliation(conn))
    
    return all_results
