"""
OpsLens Fault Matrix Tests
Tests the full lifecycle for each fault:
reset -> rebuild baselines -> verify green -> inject fault -> verify detection & trust drop -> reset -> verify resolution
"""

import pytest
from backend.db import get_connection
from data_generator.faults import FAULTS_MAP
from backend.baselines import rebuild_baselines
from backend.sentinel.run import execute_sentinel
from backend.trust.engine import calculate_all_trust_scores
from backend.lineage import get_blast_radius


@pytest.fixture(scope="module")
def conn():
    c = get_connection(schema="OPSLENS")
    yield c
    c.close()


def run_fault_lifecycle(fault_name: str, conn, expected_obj: str, expected_severity: str, expected_alert_type: str):
    """
    Executes the strict verification lifecycle for a fault:
    1. reset -> rebuild baselines -> run checks (assert 0 open alerts, all green)
    2. inject the fault -> run checks
    3. assert the expected alert exists with the right severity and affected object, and relevant trust score fell below green
    4. reset -> run checks
    5. assert alerts auto-resolved and scores are green again
    """
    # 1. Reset and establish clean baseline
    FAULT_MAPS = FAULTS_MAP
    FAULT_MAPS["reset"](conn)
    rebuild_baselines()
    sentinel_clean = execute_sentinel(conn)
    scores_clean = calculate_all_trust_scores(conn)

    assert sentinel_clean["failed"] == 0, f"Expected 0 failing checks on clean reset for {fault_name}"
    open_alerts_clean = conn.execute("SELECT COUNT(*) FROM OPSLENS.ALERTS WHERE STATUS = 'OPEN'").fetchall()[0][0]
    assert open_alerts_clean == 0, f"Expected 0 open alerts on clean reset for {fault_name}"

    clean_score_map = {s["OBJECT_NAME"]: s["TRUST_SCORE"] for s in scores_clean}
    assert clean_score_map[expected_obj] >= 85.0, f"Expected {expected_obj} to be GREEN before fault injection"
    trust_before = clean_score_map[expected_obj]

    # 2. Inject fault
    FAULT_MAPS[fault_name](conn)

    # 3. Run checks
    sentinel_fault = execute_sentinel(conn)
    scores_fault = calculate_all_trust_scores(conn)

    fault_score_map = {s["OBJECT_NAME"]: s for s in scores_fault}
    trust_after = fault_score_map[expected_obj]["TRUST_SCORE"]
    status_after = fault_score_map[expected_obj]["STATUS"]

    # Verify trust score fell below green (< 85.0)
    assert trust_after < 85.0, f"Expected {expected_obj} trust score to fall below green (<85.0), got {trust_after} ({status_after})"

    # Verify open alert exists with right severity and affected object
    alert_query = f"""
        SELECT ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY 
        FROM OPSLENS.ALERTS 
        WHERE STATUS = 'OPEN' AND TARGET_OBJECT = '{expected_obj}'
    """
    alerts = conn.execute(alert_query).fetchall()
    assert len(alerts) > 0, f"Expected open alert on {expected_obj} for fault {fault_name}, but none found"
    
    # Check severity and alert type
    matching_alerts = [a for a in alerts if a[2] == expected_severity and (expected_alert_type in a[1] or expected_alert_type in a[4])]
    assert len(matching_alerts) > 0, f"Expected alert matching severity {expected_severity} and type {expected_alert_type}. Found: {alerts}"

    alert_title = matching_alerts[0][4]

    # 4. Reset
    FAULT_MAPS["reset"](conn)
    sentinel_restored = execute_sentinel(conn)
    scores_restored = calculate_all_trust_scores(conn)

    # 5. Assert alerts auto-resolved and scores are green again
    open_alerts_restored = conn.execute("SELECT COUNT(*) FROM OPSLENS.ALERTS WHERE STATUS = 'OPEN'").fetchall()[0][0]
    assert open_alerts_restored == 0, f"Expected all alerts auto-resolved after reset, found {open_alerts_restored} open"
    
    restored_score_map = {s["OBJECT_NAME"]: s["TRUST_SCORE"] for s in scores_restored}
    assert restored_score_map[expected_obj] >= 85.0, f"Expected {expected_obj} trust score to return to GREEN after reset"

    return {
        "fault": fault_name,
        "alert_title": alert_title[:35],
        "severity": expected_severity,
        "affected_object": expected_obj,
        "trust_change": f"{trust_before:.1f} -> {trust_after:.1f}",
        "detected": "yes",
    }


def test_fault_late_load(conn):
    res = run_fault_lifecycle("late_load", conn, "ORDERS", "WARNING", "LATE_DATA_LOAD")
    assert res["detected"] == "yes"


def test_fault_row_drop(conn):
    res = run_fault_lifecycle("row_drop", conn, "ORDERS", "CRITICAL", "VOLUME_DROP_ANOMALY")
    assert res["detected"] == "yes"


def test_fault_schema_change(conn):
    res = run_fault_lifecycle("schema_change", conn, "ORDERS", "WARNING", "SCHEMA_DRIFT_DETECTED")
    assert res["detected"] == "yes"


def test_fault_duplicates(conn):
    res = run_fault_lifecycle("duplicates", conn, "LINEITEM", "CRITICAL", "PRIMARY_KEY_VIOLATION")
    assert res["detected"] == "yes"


def test_fault_revenue_mismatch(conn):
    res = run_fault_lifecycle("revenue_mismatch", conn, "ORDERS", "CRITICAL", "CROSS_TABLE_RECONCILIATION_MISMATCH")
    assert res["detected"] == "yes"


def test_fault_stale_feed(conn):
    res = run_fault_lifecycle("stale_feed", conn, "ENERGY_READINGS", "CRITICAL", "STALE_DATA_FEED")
    assert res["detected"] == "yes"


def test_fault_job_failure(conn):
    res = run_fault_lifecycle("job_failure", conn, "REVENUE_MART", "CRITICAL", "JOB_EXECUTION_FAILURE")
    assert res["detected"] == "yes"


def test_lineage_isolation(conn):
    """
    Requirement 2: Lineage isolation
    Asserts stale_feed does NOT affect Revenue Dashboard
    Asserts row_drop does NOT affect Smart Grid Dashboard
    """
    # 1. Inject stale_feed (Energy/Weather corruption)
    FAULT_MAPS = FAULTS_MAP
    FAULT_MAPS["reset"](conn)
    FAULT_MAPS["stale_feed"](conn)
    execute_sentinel(conn)
    scores = {s["OBJECT_NAME"]: s for s in calculate_all_trust_scores(conn)}
    
    # Assert Revenue Dashboard is unaffected (still GREEN, 100%)
    assert scores["Revenue Dashboard"]["STATUS"] == "GREEN"
    assert scores["Revenue Dashboard"]["TRUST_SCORE"] == 100.0
    # Assert Smart Grid Dashboard IS affected (AMBER/RED)
    assert scores["Smart Grid Dashboard"]["STATUS"] in ("AMBER", "RED")

    # Blast radius check
    blast_energy = get_blast_radius("ENERGY_READINGS", conn)
    assert "Revenue Dashboard" not in blast_energy["affected_dashboards"]
    assert "Smart Grid Dashboard" in blast_energy["affected_dashboards"]

    # 2. Reset and inject row_drop (TPCH / Orders corruption)
    FAULT_MAPS["reset"](conn)
    FAULT_MAPS["row_drop"](conn)
    execute_sentinel(conn)
    scores_drop = {s["OBJECT_NAME"]: s for s in calculate_all_trust_scores(conn)}

    # Assert Smart Grid Dashboard is unaffected (still GREEN, 100%)
    assert scores_drop["Smart Grid Dashboard"]["STATUS"] == "GREEN"
    assert scores_drop["Smart Grid Dashboard"]["TRUST_SCORE"] == 100.0
    # Assert Revenue Dashboard IS affected (fell below green)
    assert scores_drop["Revenue Dashboard"]["TRUST_SCORE"] < 85.0

    # Blast radius check
    blast_orders = get_blast_radius("ORDERS", conn)
    assert "Smart Grid Dashboard" not in blast_orders["affected_dashboards"]
    assert "Revenue Dashboard" in blast_orders["affected_dashboards"]

    # Final reset
    FAULT_MAPS["reset"](conn)
    execute_sentinel(conn)
    calculate_all_trust_scores(conn)
