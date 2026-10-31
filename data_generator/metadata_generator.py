"""
OpsLens Metadata Generator
Generates realistic simulated metadata tables:
- PIPELINE_JOBS
- PIPELINE_RUN_LOG (60 days of simulated nightly runs with stages & realistic variance)
- LINEAGE_EDGES (by hand: Sources -> Jobs -> Tables -> Marts -> Dashboards)
- CHECK_RESULTS
- ALERTS
- TRUST_SCORES
- BASELINES
All labeled as IS_SIMULATED = TRUE.
"""

import uuid
import random
from datetime import datetime, timedelta
import pandas as pd
from backend.db import get_connection

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

JOBS_DEF = [
    {
        "id": "load_orders",
        "name": "Daily Ingestion: Orders",
        "schedule": "0 1 * * *",
        "runtime_sec": 120.0,
        "source": "TPCH.ORDERS Feed",
        "target": "OPSLENS.ORDERS",
        "description": "Nightly batch extract and load of e-commerce customer orders",
        "stages": ["extract", "load", "validate"],
        "base_rows": 500,
    },
    {
        "id": "load_lineitem",
        "name": "Daily Ingestion: Line Items",
        "schedule": "0 1 * * *",
        "runtime_sec": 240.0,
        "source": "TPCH.LINEITEM Feed",
        "target": "OPSLENS.LINEITEM",
        "description": "High-volume line item transaction ingest with tax & price validation",
        "stages": ["extract", "load", "validate"],
        "base_rows": 2000,
    },
    {
        "id": "load_energy",
        "name": "Hourly Smart Meter Sync",
        "schedule": "0 2 * * *",
        "runtime_sec": 180.0,
        "source": "Energy Meter IoT Stream",
        "target": "OPSLENS.ENERGY_READINGS",
        "description": "Aggregated hourly kWh telemetry from 50 municipal power meters",
        "stages": ["extract", "load", "validate"],
        "base_rows": 1200,
    },
    {
        "id": "load_weather",
        "name": "Daily Weather Observations",
        "schedule": "0 2 * * *",
        "runtime_sec": 60.0,
        "source": "National Weather API",
        "target": "OPSLENS.WEATHER_DAILY",
        "description": "Daily temperature, precipitation, and wind speeds across cities",
        "stages": ["extract", "load", "validate"],
        "base_rows": 10,
    },
    {
        "id": "build_revenue_mart",
        "name": "Build Revenue & Grid Data Marts",
        "schedule": "0 3 * * *",
        "runtime_sec": 300.0,
        "source": "OPSLENS Raw Tables",
        "target": "OPSLENS.REVENUE_MART",
        "description": "Transform and join orders, lineitems, energy and weather into analytical marts",
        "stages": ["extract", "transform", "validate"],
        "base_rows": 2500,
    },
    {
        "id": "publish_dashboards",
        "name": "Publish Operations & BI Dashboards",
        "schedule": "0 4 * * *",
        "runtime_sec": 90.0,
        "source": "OPSLENS Marts",
        "target": "OPSLENS.DASHBOARD_METRICS",
        "description": "Push pre-aggregated KPI metrics to executive, grid, and ops dashboards",
        "stages": ["extract", "validate", "publish"],
        "base_rows": 300,
    },
]

LINEAGE_EDGES_DATA = [
    # Ingestion Feeds -> Jobs
    ("feed_tpch", "FEED", "TPC-H Ingestion Feed", "job_load_orders", "JOB", "load_orders", "READS_FROM"),
    ("feed_tpch", "FEED", "TPC-H Ingestion Feed", "job_load_lineitem", "JOB", "load_lineitem", "READS_FROM"),
    ("feed_energy", "FEED", "Smart Meter IoT Stream", "job_load_energy", "JOB", "load_energy", "READS_FROM"),
    ("feed_weather", "FEED", "NOAA Weather API", "job_load_weather", "JOB", "load_weather", "READS_FROM"),

    # Jobs -> Tables
    ("job_load_orders", "JOB", "load_orders", "tbl_orders", "TABLE", "OPSLENS.ORDERS", "WRITES_TO"),
    ("job_load_orders", "JOB", "load_orders", "tbl_customer", "TABLE", "OPSLENS.CUSTOMER", "WRITES_TO"),
    ("job_load_lineitem", "JOB", "load_lineitem", "tbl_lineitem", "TABLE", "OPSLENS.LINEITEM", "WRITES_TO"),
    ("job_load_energy", "JOB", "load_energy", "tbl_energy_readings", "TABLE", "OPSLENS.ENERGY_READINGS", "WRITES_TO"),
    ("job_load_energy", "JOB", "load_energy", "tbl_energy_meters", "TABLE", "OPSLENS.ENERGY_METERS", "WRITES_TO"),
    ("job_load_weather", "JOB", "load_weather", "tbl_weather_daily", "TABLE", "OPSLENS.WEATHER_DAILY", "WRITES_TO"),

    # Tables -> Mart Transformation Job
    ("tbl_orders", "TABLE", "OPSLENS.ORDERS", "job_build_revenue_mart", "JOB", "build_revenue_mart", "READS_FROM"),
    ("tbl_lineitem", "TABLE", "OPSLENS.LINEITEM", "job_build_revenue_mart", "JOB", "build_revenue_mart", "READS_FROM"),
    ("tbl_customer", "TABLE", "OPSLENS.CUSTOMER", "job_build_revenue_mart", "JOB", "build_revenue_mart", "READS_FROM"),
    ("tbl_energy_readings", "TABLE", "OPSLENS.ENERGY_READINGS", "job_build_revenue_mart", "JOB", "build_revenue_mart", "READS_FROM"),
    ("tbl_weather_daily", "TABLE", "OPSLENS.WEATHER_DAILY", "job_build_revenue_mart", "JOB", "build_revenue_mart", "READS_FROM"),

    # Mart Job -> Analytical Marts
    ("job_build_revenue_mart", "JOB", "build_revenue_mart", "mart_revenue", "MART", "OPSLENS.REVENUE_MART", "BUILDS"),
    ("job_build_revenue_mart", "JOB", "build_revenue_mart", "mart_grid_ops", "MART", "OPSLENS.GRID_OPS_MART", "BUILDS"),

    # Marts & Tables -> Publish Dashboards Job
    ("mart_revenue", "MART", "OPSLENS.REVENUE_MART", "job_publish_dashboards", "JOB", "publish_dashboards", "READS_FROM"),
    ("mart_grid_ops", "MART", "OPSLENS.GRID_OPS_MART", "job_publish_dashboards", "JOB", "publish_dashboards", "READS_FROM"),
    ("tbl_orders", "TABLE", "OPSLENS.ORDERS", "job_publish_dashboards", "JOB", "publish_dashboards", "READS_FROM"),
    ("tbl_energy_readings", "TABLE", "OPSLENS.ENERGY_READINGS", "job_publish_dashboards", "JOB", "publish_dashboards", "READS_FROM"),

    # Publish Job -> End Dashboards
    ("job_publish_dashboards", "JOB", "publish_dashboards", "dash_revenue", "DASHBOARD", "Revenue Analytics Dashboard", "SERVES"),
    ("job_publish_dashboards", "JOB", "publish_dashboards", "dash_energy", "DASHBOARD", "Smart Grid Energy Dashboard", "SERVES"),
    ("job_publish_dashboards", "JOB", "publish_dashboards", "dash_ops", "DASHBOARD", "OpsLens Workload & Health Dashboard", "SERVES"),
]


def populate_pipeline_jobs(conn):
    """Inserts job definitions into OPSLENS.PIPELINE_JOBS."""
    print("  -> Populating PIPELINE_JOBS...")
    conn.execute("TRUNCATE TABLE OPSLENS.PIPELINE_JOBS")
    rows = []
    now = datetime.now()
    for job in JOBS_DEF:
        rows.append({
            "JOB_ID": job["id"],
            "JOB_NAME": job["name"],
            "SCHEDULE": job["schedule"],
            "EXPECTED_RUNTIME_SEC": job["runtime_sec"],
            "SOURCE_SYSTEM": job["source"],
            "TARGET_TABLE": job["target"],
            "DESCRIPTION": job["description"],
            "IS_ACTIVE": True,
            "CREATED_AT": now,
        })
    df = pd.DataFrame(rows)
    conn.import_from_pandas(df, ("OPSLENS", "PIPELINE_JOBS"))
    print(f"     [OK] Inserted {len(rows)} job definitions")


def populate_lineage_edges(conn):
    """Populates handcrafted lineage graph edges."""
    print("  -> Populating LINEAGE_EDGES...")
    conn.execute("TRUNCATE TABLE OPSLENS.LINEAGE_EDGES")
    rows = []
    for edge in LINEAGE_EDGES_DATA:
        rows.append({
            "EDGE_ID": f"edge_{uuid.uuid4().hex[:12]}",
            "SOURCE_NODE_ID": edge[0],
            "SOURCE_NODE_TYPE": edge[1],
            "SOURCE_LABEL": edge[2],
            "TARGET_NODE_ID": edge[3],
            "TARGET_NODE_TYPE": edge[4],
            "TARGET_LABEL": edge[5],
            "RELATION_TYPE": edge[6],
        })
    df = pd.DataFrame(rows)
    conn.import_from_pandas(df, ("OPSLENS", "LINEAGE_EDGES"))
    print(f"     [OK] Inserted {len(rows)} lineage edges")


def generate_pipeline_run_log(conn, days: int = 60):
    """
    Generates 60 days of simulated nightly pipeline execution logs.
    Includes realistic Gaussian noise, sequential stages, and historical blips.
    """
    print(f"  -> Generating {days} days of PIPELINE_RUN_LOG...")
    conn.execute("TRUNCATE TABLE OPSLENS.PIPELINE_RUN_LOG")

    now = datetime.now()
    all_runs = []

    for d in range(days, 0, -1):
        run_date = (now - timedelta(days=d)).replace(hour=1, minute=0, second=0, microsecond=0)
        batch_id = f"batch_{run_date.strftime('%Y%m%d')}"

        current_time = run_date

        for job in JOBS_DEF:
            job_id = job["id"]
            expected_total_sec = job["runtime_sec"]
            stages = job["stages"]
            stage_expected_sec = expected_total_sec / len(stages)
            base_rows = job["base_rows"]

            # Historical blips / anomalies
            is_anomaly_blip = False
            blip_type = None

            # Blip 1: 45 days ago, load_lineitem transient network timeout on extract
            if d == 45 and job_id == "load_lineitem":
                is_anomaly_blip = True
                blip_type = "network_retry"
            # Blip 2: 28 days ago, build_revenue_mart latency spike (duration 3.5x)
            elif d == 28 and job_id == "build_revenue_mart":
                is_anomaly_blip = True
                blip_type = "duration_spike"
            # Blip 3: 12 days ago, load_energy validation warning
            elif d == 12 and job_id == "load_energy":
                is_anomaly_blip = True
                blip_type = "validation_warning"

            # Execute stages sequentially
            for stage_idx, stage in enumerate(stages):
                run_id = f"run_{run_date.strftime('%Y%m%d')}_{job_id}_{stage}"
                
                # Duration variance (Gaussian ± 12%)
                stage_dur = max(2.0, random.gauss(stage_expected_sec, stage_expected_sec * 0.12))
                if blip_type == "duration_spike" and stage == "transform":
                    stage_dur *= 3.8

                start_ts = current_time
                end_ts = start_ts + timedelta(seconds=stage_dur)
                current_time = end_ts + timedelta(seconds=random.randint(2, 6))

                # Row count variance (Gaussian ± 5%)
                row_var = int(random.gauss(base_rows, base_rows * 0.05))
                rows_loaded = max(0, row_var) if stage in ("load", "transform", "publish") else 0

                status = "SUCCESS"
                error_msg = None

                if blip_type == "network_retry" and stage == "extract":
                    status = "FAILED"
                    error_msg = "ConnectionResetError: Socket closed by peer during TPC-H socket stream. Auto-retried."
                elif blip_type == "validation_warning" and stage == "validate":
                    status = "WARNING"
                    error_msg = "DataQualityWarning: 5 null meter readings detected and coerced to baseline."

                all_runs.append({
                    "RUN_ID": run_id,
                    "BATCH_ID": batch_id,
                    "JOB_ID": job_id,
                    "STAGE": stage,
                    "START_TIME": start_ts,
                    "END_TIME": end_ts,
                    "DURATION_SEC": round(stage_dur, 2),
                    "STATUS": status,
                    "ROWS_LOADED": rows_loaded,
                    "ERROR_MESSAGE": error_msg,
                    "IS_SIMULATED": True,
                    "CREATED_AT": now,
                })

                # If failed retry, simulate successful retry immediately after
                if status == "FAILED":
                    retry_start = end_ts + timedelta(seconds=15)
                    retry_dur = stage_expected_sec * 1.1
                    retry_end = retry_start + timedelta(seconds=retry_dur)
                    current_time = retry_end + timedelta(seconds=2)
                    all_runs.append({
                        "RUN_ID": f"{run_id}_retry1",
                        "BATCH_ID": batch_id,
                        "JOB_ID": job_id,
                        "STAGE": stage,
                        "START_TIME": retry_start,
                        "END_TIME": retry_end,
                        "DURATION_SEC": round(retry_dur, 2),
                        "STATUS": "SUCCESS",
                        "ROWS_LOADED": rows_loaded,
                        "ERROR_MESSAGE": "Recovered on retry 1 after transient network drop",
                        "IS_SIMULATED": True,
                        "CREATED_AT": now,
                    })

    df = pd.DataFrame(all_runs)
    conn.import_from_pandas(df, ("OPSLENS", "PIPELINE_RUN_LOG"))
    print(f"     [OK] Inserted {len(all_runs):,} pipeline stage run logs across {days} days")


def generate_check_results_and_alerts(conn):
    """Generates baseline check results and recent observability alerts."""
    print("  -> Generating CHECK_RESULTS and ALERTS...")
    conn.execute("TRUNCATE TABLE OPSLENS.CHECK_RESULTS")
    conn.execute("TRUNCATE TABLE OPSLENS.ALERTS")

    now = datetime.now()

    # 1. Check Results
    checks = [
        ("chk_freshness_orders", "Orders Ingestion Freshness", "OPSLENS.ORDERS", "FRESHNESS", "CRITICAL", "PASSED", "< 24 hours", "2.4 hours", "Orders table freshness is well within SLA"),
        ("chk_null_orders_key", "Orders Primary Key Null Check", "OPSLENS.ORDERS", "NULL_CHECK", "CRITICAL", "PASSED", "0 nulls", "0 nulls", "Primary key O_ORDERKEY contains no nulls"),
        ("chk_row_count_lineitem", "Lineitem Daily Row Count", "OPSLENS.LINEITEM", "ROW_COUNT", "WARNING", "PASSED", "120,000 +/- 5%", "120,515", "Lineitem row volume is within expected range"),
        ("chk_recon_revenue", "Orders vs Lineitem Total Price Reconciliation", "OPSLENS.ORDERS", "RECONCILIATION", "CRITICAL", "PASSED", "Delta < $10.00", "$0.00", "Order total prices perfectly match summed line items"),
        ("chk_freshness_energy", "Energy Telemetry Freshness", "OPSLENS.ENERGY_READINGS", "FRESHNESS", "WARNING", "PASSED", "< 6 hours", "1.1 hours", "Smart meter stream is actively advancing"),
        ("chk_negative_kwh", "Energy Consumption Range Check", "OPSLENS.ENERGY_READINGS", "VALUE_RANGE", "CRITICAL", "PASSED", "KWH >= 0", "Min KWH = 0.012", "No negative power consumption detected"),
        ("chk_weather_coverage", "Weather City Coverage Check", "OPSLENS.WEATHER_DAILY", "COMPLETENESS", "INFO", "PASSED", "10 cities active", "10 cities active", "All municipal weather stations reported"),
        ("chk_schema_orders", "Orders Schema Invariants", "OPSLENS.ORDERS", "SCHEMA_CHECK", "CRITICAL", "PASSED", "9 standard columns", "9 standard columns", "Schema structure matches production spec"),
    ]

    check_rows = []
    for c in checks:
        check_rows.append({
            "CHECK_ID": f"chk_{uuid.uuid4().hex[:10]}",
            "CHECK_NAME": c[0],
            "TABLE_NAME": c[1],
            "CHECK_TYPE": c[2],
            "SEVERITY": c[3],
            "STATUS": c[4],
            "EXPECTED_VALUE": c[5],
            "ACTUAL_VALUE": c[6],
            "MESSAGE": c[7],
            "EXECUTED_AT": now - timedelta(minutes=random.randint(10, 180)),
            "IS_SIMULATED": True,
        })
    df_checks = pd.DataFrame(check_rows)
    conn.import_from_pandas(df_checks, ("OPSLENS", "CHECK_RESULTS"))

    # 2. Historical Alerts
    alerts = [
        ("LATE_LOAD", "MEDIUM", "OPSLENS.LINEITEM", "Late Lineitem batch ingestion", "Stage load_lineitem started 42 minutes behind schedule due to upstream source lock", "RESOLVED", now - timedelta(days=14), now - timedelta(days=14, hours=-1)),
        ("DATA_DRIFT", "LOW", "OPSLENS.ENERGY_READINGS", "Unusual weekend load surge", "Average household consumption deviated +22% from historical Sunday baseline", "RESOLVED", now - timedelta(days=7), now - timedelta(days=6)),
        ("PIPELINE_BLIP", "HIGH", "OPSLENS.REVENUE_MART", "Mart build duration spike", "build_revenue_mart exceeded p95 threshold by 310 seconds; verified clean completion", "RESOLVED", now - timedelta(days=28), now - timedelta(days=28, hours=-2)),
    ]

    alert_rows = []
    for a in alerts:
        alert_rows.append({
            "ALERT_ID": f"alt_{uuid.uuid4().hex[:10]}",
            "INCIDENT_TYPE": a[0],
            "SEVERITY": a[1],
            "TARGET_OBJECT": a[2],
            "SUMMARY": a[3],
            "DETAILS": a[4],
            "STATUS": a[5],
            "TRIGGERED_AT": a[6],
            "RESOLVED_AT": a[7],
            "IS_SIMULATED": True,
        })
    df_alerts = pd.DataFrame(alert_rows)
    conn.import_from_pandas(df_alerts, ("OPSLENS", "ALERTS"))
    print(f"     [OK] Inserted {len(check_rows)} check results and {len(alert_rows)} alerts")


def generate_trust_scores_and_baselines(conn):
    """Generates table trust scores and statistical baselines for anomaly detection."""
    print("  -> Generating TRUST_SCORES and BASELINES...")
    conn.execute("TRUNCATE TABLE OPSLENS.TRUST_SCORES")
    conn.execute("TRUNCATE TABLE OPSLENS.BASELINES")

    now = datetime.now()

    # 1. Trust Scores
    trust_items = [
        ("OPSLENS.ORDERS", "TABLE", 98.8, 99.0, 99.5, 98.0, "HEALTHY"),
        ("OPSLENS.LINEITEM", "TABLE", 97.5, 98.0, 99.0, 96.0, "HEALTHY"),
        ("OPSLENS.CUSTOMER", "TABLE", 99.9, 100.0, 100.0, 99.8, "HEALTHY"),
        ("OPSLENS.ENERGY_READINGS", "TABLE", 96.2, 95.0, 98.5, 95.5, "HEALTHY"),
        ("OPSLENS.ENERGY_METERS", "TABLE", 100.0, 100.0, 100.0, 100.0, "HEALTHY"),
        ("OPSLENS.WEATHER_DAILY", "TABLE", 99.1, 99.0, 99.5, 99.0, "HEALTHY"),
        ("OPSLENS.REVENUE_MART", "DATA_PRODUCT", 98.0, 97.5, 99.0, 97.5, "HEALTHY"),
        ("OPSLENS.GRID_OPS_MART", "DATA_PRODUCT", 96.5, 96.0, 97.0, 96.5, "HEALTHY"),
    ]

    trust_rows = []
    for t in trust_items:
        trust_rows.append({
            "SCORE_ID": f"score_{uuid.uuid4().hex[:10]}",
            "OBJECT_NAME": t[0],
            "OBJECT_TYPE": t[1],
            "TRUST_SCORE": t[2],
            "FRESHNESS_SCORE": t[3],
            "QUALITY_SCORE": t[4],
            "RELIABILITY_SCORE": t[5],
            "STATUS": t[6],
            "RECORDED_AT": now,
            "IS_SIMULATED": True,
        })
    df_trust = pd.DataFrame(trust_rows)
    conn.import_from_pandas(df_trust, ("OPSLENS", "TRUST_SCORES"))

    # 2. Baselines
    baselines = [
        ("OPSLENS.ORDERS", "DAILY_ROW_COUNT", 30000.0, 450.0, 28000.0, 32000.0, 30),
        ("OPSLENS.ORDERS", "DAILY_TOTAL_REVENUE", 45281432.0, 1200000.0, 40000000.0, 50000000.0, 30),
        ("OPSLENS.LINEITEM", "DAILY_ROW_COUNT", 120515.0, 1500.0, 115000.0, 125000.0, 30),
        ("OPSLENS.ENERGY_READINGS", "HOURLY_ROW_COUNT", 108000.0, 500.0, 100000.0, 112000.0, 30),
        ("OPSLENS.ENERGY_READINGS", "AVG_KWH_PER_READING", 1.24, 0.15, 0.70, 2.10, 30),
        ("OPSLENS.WEATHER_DAILY", "RECORDED_DAYS_COUNT", 10960.0, 50.0, 10500.0, 11200.0, 30),
        ("OPSLENS.REVENUE_MART", "BUILD_DURATION_SEC", 302.0, 28.0, 220.0, 420.0, 30),
    ]

    baseline_rows = []
    for b in baselines:
        baseline_rows.append({
            "BASELINE_ID": f"base_{uuid.uuid4().hex[:10]}",
            "OBJECT_NAME": b[0],
            "METRIC_NAME": b[1],
            "BASELINE_MEAN": b[2],
            "BASELINE_STDDEV": b[3],
            "MIN_THRESHOLD": b[4],
            "MAX_THRESHOLD": b[5],
            "WINDOW_DAYS": b[6],
            "UPDATED_AT": now,
            "IS_SIMULATED": True,
        })
    df_base = pd.DataFrame(baseline_rows)
    conn.import_from_pandas(df_base, ("OPSLENS", "BASELINES"))
    print(f"     [OK] Inserted {len(trust_rows)} trust scores and {len(baseline_rows)} metric baselines")


def generate_all_metadata(days: int = 60):
    """Executes population of all metadata and lineage tables."""
    print("=" * 60)
    print(" OpsLens — Metadata & Lineage Generation")
    print("=" * 60)
    conn = get_connection(schema="OPSLENS")
    try:
        populate_pipeline_jobs(conn)
        populate_lineage_edges(conn)
        generate_pipeline_run_log(conn, days=days)
        generate_check_results_and_alerts(conn)
        generate_trust_scores_and_baselines(conn)
        print(">> Metadata generation completed successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    generate_all_metadata()
