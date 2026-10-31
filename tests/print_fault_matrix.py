"""
OpsLens Fault Matrix Table Printer
Executes all 7 fault lifecycles, collects exact metrics, and prints the formatted table.
"""

from backend.db import get_connection
from data_generator.faults import FAULTS_MAP
from backend.baselines import rebuild_baselines
from backend.sentinel.run import execute_sentinel
from backend.trust.engine import calculate_all_trust_scores

FAULT_CONFIGS = [
    ("late_load", "ORDERS", "WARNING", "LATE_DATA_LOAD"),
    ("row_drop", "ORDERS", "CRITICAL", "VOLUME_DROP_ANOMALY"),
    ("schema_change", "ORDERS", "WARNING", "SCHEMA_DRIFT_DETECTED"),
    ("duplicates", "LINEITEM", "CRITICAL", "PRIMARY_KEY_VIOLATION"),
    ("revenue_mismatch", "ORDERS", "CRITICAL", "CROSS_TABLE_RECONCILIATION_MISMATCH"),
    ("stale_feed", "ENERGY_READINGS", "CRITICAL", "STALE_DATA_FEED"),
    ("job_failure", "REVENUE_MART", "CRITICAL", "JOB_EXECUTION_FAILURE"),
]


def run_matrix():
    conn = get_connection(schema="OPSLENS")
    results = []

    print("=" * 80)
    print(" OpsLens — Executing Comprehensive Fault Matrix Verification")
    print("=" * 80)

    try:
        for fault_name, expected_obj, expected_sev, expected_type in FAULT_CONFIGS:
            print(f"\n>> Running lifecycle test for: {fault_name} (target: {expected_obj})...")
            
            # Reset
            FAULT_MAPS = FAULTS_MAP
            FAULT_MAPS["reset"](conn)
            rebuild_baselines()
            execute_sentinel(conn)
            scores_clean = calculate_all_trust_scores(conn)
            clean_map = {s["OBJECT_NAME"]: s["TRUST_SCORE"] for s in scores_clean}
            trust_before = clean_map[expected_obj]

            # Inject
            FAULT_MAPS[fault_name](conn)
            sentinel_fault = execute_sentinel(conn)
            scores_fault = calculate_all_trust_scores(conn)
            fault_map = {s["OBJECT_NAME"]: s["TRUST_SCORE"] for s in scores_fault}
            trust_after = fault_map[expected_obj]

            # Verify alert
            alert_q = f"""
                SELECT ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY 
                FROM OPSLENS.ALERTS 
                WHERE STATUS = 'OPEN' AND TARGET_OBJECT = '{expected_obj}'
            """
            alerts = conn.execute(alert_q).fetchall()
            matching = [a for a in alerts if a[2] == expected_sev]
            alert_summary = matching[0][4] if matching else (alerts[0][4] if alerts else "None")
            detected = "yes" if matching and trust_after < 85.0 else "no"

            results.append({
                "fault": fault_name,
                "alert_title": alert_summary[:36],
                "severity": expected_sev,
                "affected_object": expected_obj,
                "trust_before_after": f"{trust_before:.1f} -> {trust_after:.1f}",
                "detected": detected,
            })

            # Cleanup
            FAULT_MAPS["reset"](conn)
            execute_sentinel(conn)
            calculate_all_trust_scores(conn)

        print("\n" + "=" * 110)
        print(f"{'fault':<18} | {'alert title':<36} | {'severity':<10} | {'affected object':<16} | {'trust before -> after':<22} | {'detected'}")
        print("-" * 110)
        for r in results:
            print(f"{r['fault']:<18} | {r['alert_title']:<36} | {r['severity']:<10} | {r['affected_object']:<16} | {r['trust_before_after']:<22} | {r['detected']}")
        print("=" * 110)

    finally:
        conn.close()


if __name__ == "__main__":
    run_matrix()
