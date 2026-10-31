"""
OpsLens Data Setup
Idempotent script that creates schema OPSLENS and copies production data from
immutable source schemas (TPCH, ENERGY, WEATHER) into OPSLENS.
NEVER writes to TPCH, ENERGY, WEATHER, SCHED, or STARTER_KIT.
"""

import os
from typing import Dict, Any
from backend.db import get_connection

COPIES = [
    {
        "target": "OPSLENS.ORDERS",
        "source": "TPCH.ORDERS",
        "description": "TPC-H Orders master dataset",
    },
    {
        "target": "OPSLENS.LINEITEM",
        "source": "TPCH.LINEITEM",
        "description": "TPC-H Line items detail dataset",
    },
    {
        "target": "OPSLENS.CUSTOMER",
        "source": "TPCH.CUSTOMER",
        "description": "TPC-H Customer accounts dataset",
    },
    {
        "target": "OPSLENS.ENERGY_READINGS",
        "source": "ENERGY.ENERGY_READINGS",
        "description": "Hourly meter energy readings (Jan-Mar 2025)",
    },
    {
        "target": "OPSLENS.ENERGY_METERS",
        "source": "ENERGY.ENERGY_METERS",
        "description": "Household meter metadata & tariffs",
    },
    {
        "target": "OPSLENS.WEATHER_DAILY",
        "source": "WEATHER.WEATHER_DAILY",
        "description": "Daily weather telemetry across cities (2023-2025)",
    },
]


def execute_sql_file(conn, file_path: str):
    """Executes all statements in a SQL script file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SQL file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by semicolon, clean comments and empty statements
    statements = [stmt.strip() for stmt in content.split(";") if stmt.strip()]
    for stmt in statements:
        # Skip pure comment blocks
        lines = [line.strip() for line in stmt.split("\n") if line.strip() and not line.strip().startswith("--")]
        if not lines:
            continue
        clean_stmt = "\n".join(lines)
        try:
            conn.execute(clean_stmt)
        except Exception as e:
            # Skip harmless table already exists or schema exists
            err_msg = str(e)
            if "already exists" in err_msg or "name already used" in err_msg:
                continue
            raise RuntimeError(f"Error executing statement: {clean_stmt[:100]}...\n{e}") from e


def setup_opslens_schema(force_reload: bool = False) -> Dict[str, int]:
    """
    Creates OPSLENS schema, initializes metadata tables, and copies
    source data into OPSLENS production tables.
    """
    print("=" * 60)
    print(" OpsLens — Data Setup & Table Initialization")
    print(f" Mode: {'FORCE RELOAD (Reset)' if force_reload else 'IDEMPOTENT SETUP'}")
    print("=" * 60)

    conn = get_connection(schema="")
    row_counts: Dict[str, int] = {}

    try:
        # 1. Ensure schema OPSLENS exists
        print("[1/4] Initializing OPSLENS schema...")
        conn.execute("CREATE SCHEMA IF NOT EXISTS OPSLENS")
        conn.execute("OPEN SCHEMA OPSLENS")

        # 2. Apply metadata tables DDL
        print("[2/4] Applying metadata tables DDL...")
        sql_path = os.path.join("sql", "02_create_metadata_tables.sql")
        execute_sql_file(conn, sql_path)

        # 3. Copy production tables from sample schemas
        print("[3/4] Syncing production tables from sample schemas into OPSLENS...")
        for item in COPIES:
            target = item["target"]
            source = item["source"]
            target_table_name = target.split(".")[1]

            # Check if table already exists and has data
            table_exists = False
            curr_count = 0
            try:
                res = conn.execute(f"SELECT COUNT(*) FROM {target}").fetchall()
                if res and res[0][0] is not None:
                    table_exists = True
                    curr_count = res[0][0]
            except Exception:
                table_exists = False

            if force_reload or not table_exists or curr_count == 0:
                print(f"  -> Copying {source} -> {target}...")
                conn.execute(f"CREATE OR REPLACE TABLE {target} AS SELECT * FROM {source}")
                res = conn.execute(f"SELECT COUNT(*) FROM {target}").fetchall()
                cnt = res[0][0] if res else 0
                row_counts[target] = cnt
                print(f"     [OK] Copied {cnt:,} rows into {target}")
            else:
                row_counts[target] = curr_count
                print(f"     [EXISTS] {target} already has {curr_count:,} rows (skipping copy)")

        # 4. Create sample marts in OPSLENS
        print("[4/4] Ensuring analytical marts exist in OPSLENS...")
        # Revenue Mart
        conn.execute("""
            CREATE OR REPLACE TABLE OPSLENS.REVENUE_MART AS
            SELECT 
                O.O_ORDERDATE AS ORDER_DATE,
                O.O_ORDERSTATUS AS ORDER_STATUS,
                O.O_ORDERPRIORITY AS ORDER_PRIORITY,
                COUNT(DISTINCT O.O_ORDERKEY) AS TOTAL_ORDERS,
                SUM(O.O_TOTALPRICE) AS TOTAL_ORDER_VALUE,
                COUNT(L.L_LINENUMBER) AS TOTAL_LINEITEMS,
                SUM(L.L_EXTENDEDPRICE * (1 - L.L_DISCOUNT)) AS NET_LINEITEM_REVENUE
            FROM OPSLENS.ORDERS O
            LEFT JOIN OPSLENS.LINEITEM L ON O.O_ORDERKEY = L.L_ORDERKEY
            GROUP BY 1, 2, 3
        """)
        res = conn.execute("SELECT COUNT(*) FROM OPSLENS.REVENUE_MART").fetchall()
        row_counts["OPSLENS.REVENUE_MART"] = res[0][0] if res else 0

        # Grid Ops Mart
        conn.execute("""
            CREATE OR REPLACE TABLE OPSLENS.GRID_OPS_MART AS
            SELECT 
                CAST(R.READING_TS AS DATE) AS USAGE_DATE,
                M.CITY,
                M.TARIFF,
                COUNT(DISTINCT R.METER_ID) AS ACTIVE_METERS,
                SUM(R.KWH) AS TOTAL_KWH,
                AVG(R.KWH) AS AVG_KWH,
                AVG(W.TEMP_AVG_C) AS AVG_TEMPERATURE
            FROM OPSLENS.ENERGY_READINGS R
            JOIN OPSLENS.ENERGY_METERS M ON R.METER_ID = M.METER_ID
            LEFT JOIN OPSLENS.WEATHER_DAILY W ON CAST(R.READING_TS AS DATE) = W.W_DATE
            GROUP BY 1, 2, 3
        """)
        res = conn.execute("SELECT COUNT(*) FROM OPSLENS.GRID_OPS_MART").fetchall()
        row_counts["OPSLENS.GRID_OPS_MART"] = res[0][0] if res else 0

        print(f"     [OK] Created OPSLENS.REVENUE_MART ({row_counts['OPSLENS.REVENUE_MART']:,} rows)")
        print(f"     [OK] Created OPSLENS.GRID_OPS_MART ({row_counts['OPSLENS.GRID_OPS_MART']:,} rows)")

        return row_counts

    finally:
        conn.close()


if __name__ == "__main__":
    counts = setup_opslens_schema(force_reload=False)
    print("\nInitial OPSLENS Production Row Counts:")
    for tbl, count in counts.items():
        print(f"  {tbl:<25}: {count:,}")
