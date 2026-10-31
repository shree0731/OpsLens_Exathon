"""
OpsLens Metadata Generator
Generates realistic simulated metadata tables:
- PIPELINE_JOBS
- PIPELINE_RUN_LOG (60 days of simulated nightly runs with 5 stages per job: extract, load, validate, transform, publish)
- LINEAGE_EDGES (by hand: Sources -> Jobs -> Tables -> Marts -> Dashboards)

NOTE: CHECK_RESULTS, ALERTS, and TRUST_SCORES are NOT populated here.
Per detection integrity rules, they are populated ONLY by the Sentinel and Trust engine.
All labeled as IS_SIMULATED = TRUE.
"""

import uuid
import random
from datetime import datetime, timedelta
import pandas as pd
from backend.db import get_connection

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# All jobs now have the 5 canonical stages
CANONICAL_STAGES = ["extract", "load", "validate", "transform", "publish"]

JOBS_DEF = [
    {
        "id": "load_orders",
        "name": "Daily Ingestion: Orders",
        "schedule": "0 1 * * *",
        "runtime_sec": 120.0,
        "source": "TPCH.ORDERS Feed",
        "target": "OPSLENS.ORDERS",
        "description": "Nightly batch extract and load of e-commerce customer orders",
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
        "base_rows": 300,
    },
]

LINEAGE_EDGES_DATA = [
    # Branch 1: TPCH Ingestion -> Orders & Lineitem -> Revenue Mart -> Revenue Dashboard
    ("feed_tpch", "source", "TPC-H Ingestion Feed", "job_load_orders", "job", "load_orders", "READS_FROM"),
    ("feed_tpch", "source", "TPC-H Ingestion Feed", "job_load_lineitem", "job", "load_lineitem", "READS_FROM"),
    ("job_load_orders", "job", "load_orders", "tbl_orders", "table", "ORDERS", "WRITES_TO"),
    ("job_load_orders", "job", "load_orders", "tbl_customer", "table", "CUSTOMER", "WRITES_TO"),
    ("job_load_lineitem", "job", "load_lineitem", "tbl_lineitem", "table", "LINEITEM", "WRITES_TO"),
    ("tbl_orders", "table", "ORDERS", "job_build_revenue_mart", "job", "build_revenue_mart", "READS_FROM"),
    ("tbl_lineitem", "table", "LINEITEM", "job_build_revenue_mart", "job", "build_revenue_mart", "READS_FROM"),
    ("tbl_customer", "table", "CUSTOMER", "job_build_revenue_mart", "job", "build_revenue_mart", "READS_FROM"),
    ("job_build_revenue_mart", "job", "build_revenue_mart", "mart_revenue", "mart", "REVENUE_MART", "BUILDS"),
    ("mart_revenue", "mart", "REVENUE_MART", "dash_revenue", "dashboard", "Revenue Dashboard", "SERVES"),

    # Branch 2: Energy Stream -> Load Energy -> Energy Tables -> Grid Mart
    ("feed_energy", "source", "Smart Meter IoT Stream", "job_load_energy", "job", "load_energy", "READS_FROM"),
    ("job_load_energy", "job", "load_energy", "tbl_energy_readings", "table", "ENERGY_READINGS", "WRITES_TO"),
    ("job_load_energy", "job", "load_energy", "tbl_energy_meters", "table", "ENERGY_METERS", "WRITES_TO"),
    ("tbl_energy_readings", "table", "ENERGY_READINGS", "mart_grid_ops", "mart", "GRID_OPS_MART", "FEEDS"),
    ("tbl_energy_meters", "table", "ENERGY_METERS", "mart_grid_ops", "mart", "GRID_OPS_MART", "FEEDS"),

    # Branch 3: Weather Feed -> Load Weather -> Weather Table -> Grid Mart -> Smart Grid Dashboard
    ("feed_weather", "source", "NOAA Weather API", "job_load_weather", "job", "load_weather", "READS_FROM"),
    ("job_load_weather", "job", "load_weather", "tbl_weather_daily", "table", "WEATHER_DAILY", "WRITES_TO"),
    ("tbl_weather_daily", "table", "WEATHER_DAILY", "mart_grid_ops", "mart", "GRID_OPS_MART", "FEEDS"),
    ("mart_grid_ops", "mart", "GRID_OPS_MART", "dash_grid", "dashboard", "Smart Grid Dashboard", "SERVES"),

    # Executive Ops Dashboard depends on BOTH Marts
    ("mart_revenue", "mart", "REVENUE_MART", "job_publish_dashboards", "job", "publish_dashboards", "READS_FROM"),
    ("mart_grid_ops", "mart", "GRID_OPS_MART", "job_publish_dashboards", "job", "publish_dashboards", "READS_FROM"),
    ("job_publish_dashboards", "job", "publish_dashboards", "dash_ops", "dashboard", "Executive Ops Dashboard", "SERVES"),
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
    Includes all 5 stages (extract, load, validate, transform, publish) per job per day.
    """
    print(f"  -> Generating {days} days of PIPELINE_RUN_LOG (all 5 canonical stages)...")
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
            # 5 canonical stages
            stage_expected_sec = expected_total_sec / 5.0
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

            # Execute all 5 stages sequentially: extract, load, validate, transform, publish
            for stage_idx, stage in enumerate(CANONICAL_STAGES):
                run_id = f"run_{run_date.strftime('%Y%m%d')}_{job_id}_{stage}"
                
                # Duration variance (Gaussian ± 12%)
                stage_dur = max(2.0, random.gauss(stage_expected_sec, stage_expected_sec * 0.12))
                if blip_type == "duration_spike" and stage == "transform":
                    stage_dur *= 3.8

                start_ts = current_time
                end_ts = start_ts + timedelta(seconds=stage_dur)
                current_time = end_ts + timedelta(seconds=random.randint(1, 4))

                # Row count variance (Gaussian ± 5%)
                row_var = int(random.gauss(base_rows, base_rows * 0.05))
                # Rows reported on load / transform / publish
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
    print(f"     [OK] Inserted {len(all_runs):,} pipeline stage run logs (6 jobs x 5 stages x {days} days)")


def generate_all_metadata(days: int = 60):
    """Executes population of metadata and lineage tables."""
    print("=" * 60)
    print(" OpsLens — Metadata & Lineage Generation")
    print("=" * 60)
    conn = get_connection(schema="OPSLENS")
    try:
        populate_pipeline_jobs(conn)
        populate_lineage_edges(conn)
        generate_pipeline_run_log(conn, days=days)
        print(">> Metadata generation completed successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    generate_all_metadata()
