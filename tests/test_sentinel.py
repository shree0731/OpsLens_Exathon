"""
Unit and integration tests for OpsLens Sentinel detectors.
"""

import pytest
from backend.db import get_connection
from backend.sentinel.detectors import (
    check_late_or_failed_jobs,
    check_row_count_anomalies,
    check_runtime_anomalies,
    check_schema_drift,
    check_stale_feeds,
    check_duplicate_keys,
    check_reconciliation,
    run_all_detectors,
)
from backend.sentinel.run import execute_sentinel


@pytest.fixture(scope="module")
def conn():
    c = get_connection(schema="OPSLENS")
    yield c
    c.close()


def test_detector_schema_and_types(conn):
    results = run_all_detectors(conn)
    assert len(results) >= 15

    for r in results:
        assert "check_id" in r
        assert "check_name" in r
        assert "table_name" in r
        assert "check_type" in r
        assert r["severity"] in ("INFO", "WARNING", "CRITICAL")
        assert r["status"] in ("PASS", "FAIL")
        assert "message" in r


def test_clean_state_all_pass(conn):
    # On clean state, all detectors should pass
    results = run_all_detectors(conn)
    failing = [r for r in results if r["status"] == "FAIL"]
    assert len(failing) == 0, f"Expected 0 failing checks on clean state, found {len(failing)}: {failing}"


def test_reconciliation_zero_mismatch(conn):
    res = check_reconciliation(conn)
    assert len(res) == 1
    assert res[0]["status"] == "PASS"
    assert "0 mismatched" in res[0]["actual_value"]


def test_duplicate_keys_clean(conn):
    res = check_duplicate_keys(conn)
    assert len(res) == 2
    for r in res:
        assert r["status"] == "PASS"
        assert r["actual_value"] == "0 duplicates"


def test_stale_feeds_clean(conn):
    res = check_stale_feeds(conn)
    assert len(res) >= 2
    for r in res:
        assert r["status"] == "PASS"


def test_execute_sentinel_cycle(conn):
    summary = execute_sentinel(conn)
    assert summary["total_checks"] >= 20
    assert summary["failed"] == 0
    assert summary["passed"] == summary["total_checks"]
