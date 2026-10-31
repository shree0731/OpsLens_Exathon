"""
OpsLens Data Discovery Script
Discovers schema details, column types, row counts, and date ranges for:
- SCHED.SCHED_TASKS
- SCHED.SCHED_HISTORY
- ENERGY.ENERGY_READINGS
- ENERGY.ENERGY_METERS
- WEATHER.WEATHER_DAILY
- TPCH.ORDERS
- TPCH.LINEITEM

Also checks which EXA_* system/audit views are queryable for query history and performance monitoring.
Saves all findings directly to docs/data_discovery.md without inventing any data.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from backend.db import get_connection, get_db_config

TARGET_TABLES = [
    ("SCHED", "SCHED_TASKS"),
    ("SCHED", "SCHED_HISTORY"),
    ("ENERGY", "ENERGY_READINGS"),
    ("ENERGY", "ENERGY_METERS"),
    ("WEATHER", "WEATHER_DAILY"),
    ("TPCH", "ORDERS"),
    ("TPCH", "LINEITEM"),
]

SYSTEM_VIEWS_TO_TEST = [
    # Session and Query History Views
    "SYS.EXA_ALL_SESSIONS",
    "SYS.EXA_USER_SESSIONS",
    "SYS.EXA_DBA_SESSIONS",
    "SYS.EXA_ALL_AUDIT_SQL",
    "SYS.EXA_USER_AUDIT_SQL",
    "SYS.EXA_DBA_AUDIT_SQL",
    "SYS.EXA_ALL_AUDIT_SESSIONS",
    "SYS.EXA_ALL_QUERIES",
    "SYS.EXA_USER_QUERIES",
    "SYS.EXA_DBA_QUERIES",
    "SYS.EXA_ALL_STATEMENTS",
    # Exasol Statistics Schema
    "EXA_STATISTICS.EXA_MONITORING_DAILY",
    "EXA_STATISTICS.EXA_SQL_HOURLY",
    "EXA_STATISTICS.EXA_SQL_DAILY",
    "EXA_STATISTICS.EXA_USAGE_HOURLY",
    "EXA_STATISTICS.EXA_USAGE_DAILY",
    "EXA_STATISTICS.EXA_CLUSTER_HOURLY",
    "EXA_STATISTICS.EXA_CLUSTER_DAILY",
    # System metadata
    "SYS.EXA_ALL_SCHEMAS",
    "SYS.EXA_ALL_TABLES",
    "SYS.EXA_ALL_COLUMNS",
]


def run_discovery() -> Dict[str, Any]:
    config = get_db_config()
    print("=" * 70)
    print(" OpsLens — Automated Data & System View Discovery")
    print("=" * 70)
    print(f"Connecting to Exasol at {config['dsn']} (verify_cert={config['verify_cert']})...")

    conn = get_connection(schema="")
    discovery_data = {
        "timestamp": datetime.now().isoformat(),
        "dsn": config["dsn"],
        "user": config["user"],
        "tables": {},
        "system_views": {},
        "discovered_schemas": [],
    }

    # 1. Discover all accessible schemas
    print("\n[1/3] Querying available schemas in Exasol...")
    try:
        schemas_res = conn.execute(
            "SELECT SCHEMA_NAME, SCHEMA_OWNER FROM SYS.EXA_ALL_SCHEMAS ORDER BY SCHEMA_NAME"
        ).fetchall()
        discovery_data["discovered_schemas"] = [
            {"name": r[0], "owner": r[1]} for r in schemas_res
        ]
        print(f"Found {len(schemas_res)} schemas: {[r[0] for r in schemas_res]}")
    except Exception as e:
        print(f"Could not query SYS.EXA_ALL_SCHEMAS: {e}")
        discovery_data["discovered_schemas_error"] = str(e)

    # 2. Inspect Target Tables
    print("\n[2/3] Inspecting target sample tables...")
    for schema_name, table_name in TARGET_TABLES:
        full_table = f"{schema_name}.{table_name}"
        print(f"  -> Discovering {full_table}...")
        table_info: Dict[str, Any] = {
            "schema": schema_name,
            "table": table_name,
            "exists": False,
            "row_count": None,
            "columns": [],
            "date_ranges": {},
            "error": None,
        }

        try:
            # Query column metadata from SYS.EXA_ALL_COLUMNS
            cols_query = (
                f"SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_IS_NULLABLE, COLUMN_ORDINAL_POSITION "
                f"FROM SYS.EXA_ALL_COLUMNS "
                f"WHERE COLUMN_SCHEMA = '{schema_name}' AND COLUMN_TABLE = '{table_name}' "
                f"ORDER BY COLUMN_ORDINAL_POSITION"
            )
            cols_res = conn.execute(cols_query).fetchall()

            if not cols_res:
                # Try fallback DESCRIBE or cursor column metadata
                try:
                    stmt = conn.execute(f"SELECT * FROM {full_table} LIMIT 0")
                    # Columns description from pyexasol statement
                    cols_res = [
                        (col_name, str(col_meta.get("type", "UNKNOWN")), True, idx + 1)
                        for idx, (col_name, col_meta) in enumerate(stmt.columns().items())
                    ]
                except Exception as inner_e:
                    table_info["error"] = f"Table not found or inaccessible: {inner_e}"
                    discovery_data["tables"][full_table] = table_info
                    print(f"     [FAILED] {full_table}: {table_info['error']}")
                    continue

            table_info["exists"] = True
            for col in cols_res:
                c_name, c_type, c_null, c_pos = col[0], col[1], col[2], col[3]
                table_info["columns"].append({
                    "name": c_name,
                    "type": str(c_type),
                    "nullable": c_null,
                    "position": c_pos,
                })

            # Row count
            cnt_res = conn.execute(f"SELECT COUNT(*) FROM {full_table}").fetchall()
            table_info["row_count"] = cnt_res[0][0] if cnt_res else 0

            # Date / Timestamp range discovery
            date_cols = [
                c["name"]
                for c in table_info["columns"]
                if any(t in c["type"].upper() for t in ("DATE", "TIMESTAMP", "TIME"))
            ]

            for dcol in date_cols:
                try:
                    range_q = f"SELECT MIN({dcol}), MAX({dcol}) FROM {full_table}"
                    range_res = conn.execute(range_q).fetchall()
                    if range_res and range_res[0]:
                        table_info["date_ranges"][dcol] = {
                            "min": str(range_res[0][0]),
                            "max": str(range_res[0][1]),
                        }
                except Exception as range_e:
                    table_info["date_ranges"][dcol] = {"error": str(range_e)}

            print(
                f"     [OK] {full_table}: {len(table_info['columns'])} columns, "
                f"{table_info['row_count']} rows, date ranges: {list(table_info['date_ranges'].keys())}"
            )

        except Exception as e:
            table_info["error"] = str(e)
            print(f"     [ERROR] {full_table}: {e}")

        discovery_data["tables"][full_table] = table_info

    # 3. Test System / Audit Views for Query History
    print("\n[3/3] Checking queryability of EXA_* system & audit views...")
    for view_name in SYSTEM_VIEWS_TO_TEST:
        view_info: Dict[str, Any] = {
            "view": view_name,
            "queryable": False,
            "columns": [],
            "sample_row_count": None,
            "error": None,
        }
        try:
            stmt = conn.execute(f"SELECT * FROM {view_name} LIMIT 1")
            view_info["queryable"] = True
            if hasattr(stmt, "columns") and callable(stmt.columns):
                view_info["columns"] = list(stmt.columns().keys())
            
            # Check if there is data
            sample = stmt.fetchall()
            view_info["sample_row_count"] = len(sample)
            print(f"  -> [OK] {view_name} is queryable ({len(view_info['columns'])} columns)")
        except Exception as ve:
            view_info["error"] = str(ve)
            print(f"  -> [FAIL] {view_name}: {ve}")

        discovery_data["system_views"][view_name] = view_info

    conn.close()
    return discovery_data


def generate_markdown_report(discovery_data: Dict[str, Any], output_path: str):
    """Formats discovery results into docs/data_discovery.md markdown document."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    lines = [
        "# OpsLens — Exasol Data & System Discovery Report",
        "",
        f"**Discovery Run Date:** `{discovery_data.get('timestamp')}`  ",
        f"**Target Exasol DSN:** `{discovery_data.get('dsn')}`  ",
        f"**User Account:** `{discovery_data.get('user')}`  ",
        "",
        "---",
        "",
        "## 1. Discovered Schemas in Database",
        "",
    ]

    schemas = discovery_data.get("discovered_schemas", [])
    if schemas:
        lines.append("| Schema Name | Schema Owner |")
        lines.append("| :--- | :--- |")
        for s in schemas:
            lines.append(f"| `{s['name']}` | `{s['owner']}` |")
    else:
        err = discovery_data.get("discovered_schemas_error", "No schemas returned")
        lines.append(f"> [!WARNING]\n> Failed to list schemas: `{err}`")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Sample Target Tables Discovery",
        "",
        "Per project rules, schemas `ENERGY`, `SCHED`, `WEATHER`, and `TPCH` are immutable reference datasets.",
        "",
    ])

    for full_table, tbl in discovery_data.get("tables", {}).items():
        lines.append(f"### Table: `{full_table}`")
        lines.append("")
        if not tbl.get("exists"):
            lines.append(f"> [!CAUTION]\n> **Inaccessible or Missing:** {tbl.get('error')}")
            lines.append("")
            continue

        lines.append(f"- **Row Count:** `{tbl.get('row_count'):,}`")
        lines.append(f"- **Total Columns:** `{len(tbl.get('columns', []))}`")
        lines.append("")
        
        # Date ranges
        if tbl.get("date_ranges"):
            lines.append("**Date/Timestamp Ranges:**")
            lines.append("| Column | Min Value | Max Value |")
            lines.append("| :--- | :--- | :--- |")
            for col, rng in tbl["date_ranges"].items():
                if "error" in rng:
                    lines.append(f"| `{col}` | *Error: {rng['error']}* | - |")
                else:
                    lines.append(f"| `{col}` | `{rng.get('min')}` | `{rng.get('max')}` |")
            lines.append("")

        # Columns table
        lines.append("**Columns & Data Types:**")
        lines.append("| # | Column Name | Data Type | Nullable |")
        lines.append("| :-: | :--- | :--- | :-: |")
        for col in tbl.get("columns", []):
            lines.append(
                f"| {col['position']} | **`{col['name']}`** | `{col['type']}` | {col['nullable']} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "## 3. System & Audit Views Queryability (Query History)",
        "",
        "Evaluation of `EXA_*` audit and system views for operational intelligence, query telemetry, and performance tracking.",
        "",
        "| System / Audit View | Queryable? | Columns Available | Status / Exact Error |",
        "| :--- | :-: | :--- | :--- |",
    ])

    for view_name, vinfo in discovery_data.get("system_views", {}).items():
        q_status = "YES" if vinfo["queryable"] else "NO"
        cols_count = f"{len(vinfo['columns'])} columns" if vinfo["queryable"] else "-"
        detail = "Accessible" if vinfo["queryable"] else f"Error: {vinfo.get('error')}"
        lines.append(f"| `{view_name}` | **{q_status}** | {cols_count} | {detail} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### Detailed Column Sets for Queryable Audit Views")
    lines.append("")

    for view_name, vinfo in discovery_data.get("system_views", {}).items():
        if vinfo["queryable"] and vinfo.get("columns"):
            lines.append(f"#### `{view_name}`")
            lines.append("`" + "`, `".join(vinfo["columns"]) + "`")
            lines.append("")

    report_content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n>> Discovery findings saved to: {output_path}")


def main():
    report_file = os.path.join("docs", "data_discovery.md")
    try:
        data = run_discovery()
        generate_markdown_report(data, report_file)
        print("\nDiscovery completed successfully!")
    except Exception as exc:
        print("\n" + "!" * 70)
        print(" Discovery execution halted due to connection or system failure.")
        print("!" * 70)
        print(f"Exact Error: {exc}\n")

        # Write error notice to docs/data_discovery.md
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# OpsLens — Data Discovery Report\n\n")
            f.write(f"**Execution Timestamp:** `{datetime.now().isoformat()}`\n\n")
            f.write(f"> [!CAUTION]\n> **Discovery Failed to Connect:**\n> ```\n{exc}\n```\n\n")
            f.write(f"Please check that Exasol is running and credentials in `.env` are accurate.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
