"""
OpsLens Data Generator Master Orchestrator
Usage: python -m data_generator.main

Executes:
1. Production data copy into OPSLENS (idempotent)
2. Metadata & lineage generation (PIPELINE_RUN_LOG, JOBS, CHECK_RESULTS, ALERTS, TRUST_SCORES, BASELINES, LINEAGE_EDGES)
3. Simulated query telemetry generation (QUERY_STATS for Cost Radar)
4. Displays row counts per OPSLENS table
"""

import sys
from backend.db import get_connection
from data_generator.setup_data import setup_opslens_schema
from data_generator.metadata_generator import generate_all_metadata
from data_generator.workload_generator import run_workload_generator


def get_all_opslens_counts() -> dict:
    """Queries row counts for all tables and views in OPSLENS schema."""
    conn = get_connection(schema="OPSLENS")
    try:
        tables = conn.execute(
            "SELECT TABLE_NAME FROM SYS.EXA_ALL_TABLES WHERE TABLE_SCHEMA = 'OPSLENS' ORDER BY TABLE_NAME"
        ).fetchall()
        counts = {}
        for t in tables:
            t_name = t[0]
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM OPSLENS.{t_name}").fetchall()[0][0]
                counts[t_name] = cnt
            except Exception as e:
                counts[t_name] = f"Error: {e}"
        return counts
    finally:
        conn.close()


def print_table_summary(counts: dict, title: str = "OPSLENS Tables & Row Counts"):
    """Prints a clean tabular report of table counts."""
    print("\n" + "=" * 65)
    print(f" {title}")
    print("=" * 65)
    print(f" {'Table Name':<30} | {'Row Count':>15} | {'Type':<12}")
    print("-" * 65)
    for tbl, cnt in counts.items():
        if tbl in ("ORDERS", "LINEITEM", "CUSTOMER", "ENERGY_READINGS", "ENERGY_METERS", "WEATHER_DAILY"):
            t_type = "Production"
        elif tbl in ("REVENUE_MART", "GRID_OPS_MART"):
            t_type = "Data Mart"
        else:
            t_type = "Metadata"
        formatted_cnt = f"{cnt:,}" if isinstance(cnt, int) else str(cnt)
        print(f" {tbl:<30} | {formatted_cnt:>15} | {t_type:<12}")
    print("=" * 65 + "\n")


def run_full_pipeline():
    print("\n" + "#" * 65)
    print(" OpsLens — End-to-End Synthetic Data & Workload Setup")
    print("#" * 65 + "\n")

    # Step 1: Copy production tables from sample schemas
    setup_opslens_schema(force_reload=False)

    # Step 2: Generate metadata, 60-day run history, lineage edges, and alerts
    generate_all_metadata(days=60)

    # Step 3: Generate simulated query telemetry for Cost Radar
    run_workload_generator()

    # Step 4: Display final row counts
    counts = get_all_opslens_counts()
    print_table_summary(counts, "Final OPSLENS Tables & Row Counts")
    return counts


if __name__ == "__main__":
    run_full_pipeline()
