"""
Unit and integration tests for OpsLens Lineage and Blast Radius analysis.
"""

from backend.lineage import get_lineage_graph, get_blast_radius


def test_lineage_graph_structure():
    g = get_lineage_graph()
    assert "nodes" in g
    assert "edges" in g
    assert g["total_nodes"] >= 15
    assert g["total_edges"] >= 20

    node_ids = {n["id"] for n in g["nodes"]}
    for e in g["edges"]:
        assert e["source"] in node_ids
        assert e["target"] in node_ids


def test_blast_radius_traversal():
    b = get_blast_radius("OPSLENS.ENERGY_READINGS")
    assert b["affected_count"] > 0
    assert len(b["affected_dashboards"]) > 0
    assert any("Energy" in d or "Smart Grid" in d for d in b["affected_dashboards"])


def test_blast_radius_orders():
    b = get_blast_radius("ORDERS")
    assert b["affected_count"] > 0
    assert any("Revenue" in d for d in b["affected_dashboards"])
