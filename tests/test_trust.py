"""
Unit and integration tests for OpsLens Trust Score Engine.
"""

import pytest
from backend.db import get_connection
from backend.trust.engine import (
    get_status,
    calculate_all_trust_scores,
    STATUS_GREEN_MIN,
    STATUS_AMBER_MIN,
    WEIGHT_FRESHNESS,
    WEIGHT_COMPLETENESS,
    WEIGHT_UNIQUENESS,
    WEIGHT_CONSISTENCY,
)


def test_weights_sum_to_one():
    total_weights = WEIGHT_FRESHNESS + WEIGHT_COMPLETENESS + WEIGHT_UNIQUENESS + WEIGHT_CONSISTENCY
    assert round(total_weights, 4) == 1.0


def test_status_thresholds():
    assert get_status(100.0) == "GREEN"
    assert get_status(85.0) == "GREEN"
    assert get_status(84.9) == "AMBER"
    assert get_status(60.0) == "AMBER"
    assert get_status(59.9) == "RED"
    assert get_status(0.0) == "RED"


def test_clean_state_all_green():
    conn = get_connection(schema="OPSLENS")
    try:
        scores = calculate_all_trust_scores(conn)
        assert len(scores) >= 10

        for s in scores:
            assert s["STATUS"] == "GREEN"
            assert s["TRUST_SCORE"] >= STATUS_GREEN_MIN
            assert s["FRESHNESS_SCORE"] == 100.0
            assert s["COMPLETENESS_SCORE"] == 100.0
            assert s["UNIQUENESS_SCORE"] == 100.0
            assert s["CONSISTENCY_SCORE"] == 100.0
    finally:
        conn.close()


def test_dashboard_inheritance():
    conn = get_connection(schema="OPSLENS")
    try:
        scores = calculate_all_trust_scores(conn)
        scores_by_name = {s["OBJECT_NAME"]: s for s in scores}

        # Revenue Dashboard should inherit from REVENUE_MART
        assert "Revenue Dashboard" in scores_by_name
        assert "REVENUE_MART" in scores_by_name
        assert scores_by_name["Revenue Dashboard"]["TRUST_SCORE"] <= scores_by_name["REVENUE_MART"]["TRUST_SCORE"]

        # Grid Ops Dashboard should inherit from GRID_OPS_MART
        assert "Grid Ops Dashboard" in scores_by_name
        assert "GRID_OPS_MART" in scores_by_name
        assert scores_by_name["Grid Ops Dashboard"]["TRUST_SCORE"] <= scores_by_name["GRID_OPS_MART"]["TRUST_SCORE"]
    finally:
        conn.close()
