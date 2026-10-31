"""
OpsLens Lineage Impact Analysis Module
Constructs directed dependency graph from OPSLENS.LINEAGE_EDGES.
Computes downstream blast radius and upstream root causes.
"""

from typing import Dict, Any, List, Set, Optional
from collections import defaultdict, deque
from backend.db import get_connection


def fetch_lineage_data(conn=None):
    """Fetches edges and current trust scores from Exasol."""
    should_close = False
    if conn is None:
        conn = get_connection(schema="OPSLENS")
        should_close = True

    try:
        # Fetch edges
        edges_rows = conn.execute("""
            SELECT 
                EDGE_ID, 
                SOURCE_NODE_ID, 
                SOURCE_NODE_TYPE, 
                SOURCE_LABEL, 
                TARGET_NODE_ID, 
                TARGET_NODE_TYPE, 
                TARGET_LABEL, 
                RELATION_TYPE
            FROM OPSLENS.LINEAGE_EDGES
        """).fetchall()

        # Fetch trust scores
        scores_rows = conn.execute("""
            SELECT OBJECT_NAME, TRUST_SCORE, STATUS 
            FROM OPSLENS.TRUST_SCORES
        """).fetchall()
        trust_map = {r[0]: {"trust_score": float(r[1]), "status": r[2]} for r in scores_rows}

        # Fetch active alerts
        alert_rows = conn.execute("""
            SELECT TARGET_OBJECT, INCIDENT_TYPE, SEVERITY 
            FROM OPSLENS.ALERTS 
            WHERE STATUS = 'OPEN'
        """).fetchall()
        alerts_map = defaultdict(list)
        for r in alert_rows:
            obj_clean = r[0].replace("OPSLENS.", "").strip()
            alerts_map[obj_clean].append({"type": r[1], "severity": r[2]})

        return edges_rows, trust_map, alerts_map

    finally:
        if should_close and conn:
            conn.close()


def get_lineage_graph(conn=None) -> Dict[str, Any]:
    """
    Returns complete lineage graph with nodes and directed edges.
    Nodes include type, label, trust_score, status, and active alerts.
    """
    edges_rows, trust_map, alerts_map = fetch_lineage_data(conn)

    nodes_dict: Dict[str, Dict[str, Any]] = {}
    edges_list: List[Dict[str, Any]] = []

    for r in edges_rows:
        edge_id, src_id, src_type, src_lbl, tgt_id, tgt_type, tgt_lbl, rel_type = r

        # Add Source Node
        if src_id not in nodes_dict:
            src_clean = src_id.replace("OPSLENS.", "").strip()
            trust_info = trust_map.get(src_clean) or trust_map.get(src_lbl) or {"trust_score": 100.0, "status": "GREEN"}
            has_critical = any(a["severity"] == "CRITICAL" for a in alerts_map.get(src_clean, []))
            node_status = "RED" if has_critical else trust_info["status"]
            
            nodes_dict[src_id] = {
                "id": src_id,
                "label": src_lbl,
                "type": src_type,
                "trust_score": trust_info["trust_score"],
                "status": node_status,
                "active_alerts": alerts_map.get(src_clean, []),
            }

        # Add Target Node
        if tgt_id not in nodes_dict:
            tgt_clean = tgt_id.replace("OPSLENS.", "").strip()
            trust_info = trust_map.get(tgt_clean) or trust_map.get(tgt_lbl) or {"trust_score": 100.0, "status": "GREEN"}
            has_critical = any(a["severity"] == "CRITICAL" for a in alerts_map.get(tgt_clean, []))
            node_status = "RED" if has_critical else trust_info["status"]

            nodes_dict[tgt_id] = {
                "id": tgt_id,
                "label": tgt_lbl,
                "type": tgt_type,
                "trust_score": trust_info["trust_score"],
                "status": node_status,
                "active_alerts": alerts_map.get(tgt_clean, []),
            }

        # Add Edge
        edges_list.append({
            "edge_id": edge_id,
            "source": src_id,
            "target": tgt_id,
            "relation_type": rel_type,
        })

    return {
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
        "total_nodes": len(nodes_dict),
        "total_edges": len(edges_list),
    }


def get_blast_radius(node_id: str, conn=None) -> Dict[str, Any]:
    """
    Performs breadth-first traversal from node_id along downstream edges
    to determine all downstream tables, marts, and dashboards impacted.
    Also traverses upstream to find root source dependencies.
    """
    edges_rows, trust_map, alerts_map = fetch_lineage_data(conn)

    # Build adjacency lists
    downstream_adj: Dict[str, List[str]] = defaultdict(list)
    upstream_adj: Dict[str, List[str]] = defaultdict(list)
    node_meta: Dict[str, Dict[str, Any]] = {}

    for r in edges_rows:
        _, src_id, src_type, src_lbl, tgt_id, tgt_type, tgt_lbl, _ = r
        downstream_adj[src_id].append(tgt_id)
        upstream_adj[tgt_id].append(src_id)

        if src_id not in node_meta:
            node_meta[src_id] = {"id": src_id, "type": src_type, "label": src_lbl}
        if tgt_id not in node_meta:
            node_meta[tgt_id] = {"id": tgt_id, "type": tgt_type, "label": tgt_lbl}

    # Normalize node_id (support ID, label, or qualified name)
    target_node = None
    target_query = node_id.strip()
    target_clean = target_query.replace("OPSLENS.", "").lower()

    for k, v in node_meta.items():
        lbl = v.get("label", "")
        lbl_clean = lbl.replace("OPSLENS.", "").lower()
        k_clean = k.replace("tbl_", "").replace("job_", "").replace("mart_", "").replace("dash_", "").replace("feed_", "").lower()
        if (
            k == target_query
            or k.lower() == target_query.lower()
            or lbl == target_query
            or lbl.lower() == target_query.lower()
            or lbl_clean == target_clean
            or k_clean == target_clean
        ):
            target_node = k
            break

    if not target_node:
        target_node = node_id
        node_meta[target_node] = {"id": target_node, "type": "UNKNOWN", "label": target_node}

    # BFS Downstream (Blast Radius)
    visited_down: Set[str] = set()
    queue = deque([target_node])
    affected_nodes = []
    affected_dashboards = []
    affected_marts = []

    while queue:
        curr = queue.popleft()
        for child in downstream_adj.get(curr, []):
            if child not in visited_down:
                visited_down.add(child)
                queue.append(child)
                child_meta = node_meta.get(child, {"id": child, "type": "UNKNOWN", "label": child})
                affected_nodes.append(child_meta)
                if child_meta["type"] == "DASHBOARD":
                    affected_dashboards.append(child_meta["label"])
                elif child_meta["type"] == "MART":
                    affected_marts.append(child_meta["label"])

    # BFS Upstream (Root Causes)
    visited_up: Set[str] = set()
    queue_up = deque([target_node])
    upstream_sources = []

    while queue_up:
        curr = queue_up.popleft()
        parents = upstream_adj.get(curr, [])
        if not parents:
            meta = node_meta.get(curr, {"id": curr, "type": "SOURCE", "label": curr})
            if meta["id"] != target_node:
                upstream_sources.append(meta)
        for parent in parents:
            if parent not in visited_up:
                visited_up.add(parent)
                queue_up.append(parent)

    return {
        "target_node": node_meta.get(target_node, {"id": target_node}),
        "impact_summary": f"Incident on {target_node} cascades to {len(affected_nodes)} downstream dependencies across {len(affected_dashboards)} business dashboards.",
        "affected_count": len(affected_nodes),
        "affected_dashboards": list(set(affected_dashboards)),
        "affected_marts": list(set(affected_marts)),
        "affected_nodes": affected_nodes,
        "upstream_sources": upstream_sources,
    }
