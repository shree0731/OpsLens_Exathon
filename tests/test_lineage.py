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


def test_lineage_response_shape_and_blast_radius():
    g = get_lineage_graph()
    assert "nodes" in g
    assert "edges" in g

    # Validate edge format: source, target, relation
    for edge in g["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "relation" in edge or "relation_type" in edge

    # Validate node fields
    for node in g["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "type" in node
        assert "trust_score" in node
        assert "status" in node
        assert "active_alerts" in node
        assert "inherited_from" in node
        
        # If node has open alert or is degraded, blast_radius must be present with required structure
        if node["status"] != "GREEN" or len(node["active_alerts"]) > 0:
            assert node["blast_radius"] is not None
            br = node["blast_radius"]
            assert "summary" in br
            assert "affected_count" in br
            assert "affected_node_ids" in br
            assert "by_type" in br
            assert "tables" in br["summary"] and "marts" in br["summary"] and "dashboards" in br["summary"]
            assert "table" in br["by_type"]
            assert "mart" in br["by_type"]
            assert "dashboard" in br["by_type"]
