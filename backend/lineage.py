"""
OpsLens Lineage Impact Analysis Module
Constructs directed dependency graph from OPSLENS.LINEAGE_EDGES.
Computes downstream blast radius and upstream root causes.
"""

from typing import Dict, Any, List, Set, Optional
from collections import defaultdict, deque
from backend.db import get_connection


def fetch_lineage_data(conn=None):
    """Fetches edges, current trust scores, active alerts, and latest job runs from Exasol."""
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
            SELECT OBJECT_NAME, OBJECT_TYPE, TRUST_SCORE, 
                   FRESHNESS_SCORE, COMPLETENESS_SCORE, UNIQUENESS_SCORE, CONSISTENCY_SCORE, STATUS 
            FROM OPSLENS.TRUST_SCORES
        """).fetchall()
        trust_map = {
            r[0]: {
                "object_name": r[0],
                "object_type": r[1],
                "trust_score": float(r[2]),
                "freshness_score": float(r[3]),
                "completeness_score": float(r[4]),
                "uniqueness_score": float(r[5]),
                "consistency_score": float(r[6]),
                "status": r[7],
            }
            for r in scores_rows
        }

        # Fetch active open alerts
        alert_rows = conn.execute("""
            SELECT ALERT_ID, INCIDENT_TYPE, SEVERITY, TARGET_OBJECT, SUMMARY, DETAILS, 
                   SUGGESTED_ROOT_CAUSE, RECOMMENDED_ACTION, STATUS, FIRST_SEEN
            FROM OPSLENS.ALERTS 
            WHERE STATUS = 'OPEN'
        """).fetchall()
        
        all_alerts = [
            {
                "alert_id": r[0],
                "incident_type": r[1],
                "severity": r[2],
                "target_object": r[3],
                "summary": r[4],
                "details": r[5],
                "suggested_root_cause": r[6],
                "recommended_action": r[7],
                "status": r[8],
                "first_seen": str(r[9]),
            }
            for r in alert_rows
        ]

        # Fetch latest run per job
        run_rows = conn.execute("""
            SELECT JOB_ID, STAGE, STATUS, START_TIME, END_TIME, DURATION_SEC, ROWS_LOADED, ERROR_MESSAGE
            FROM OPSLENS.PIPELINE_RUN_LOG
            ORDER BY START_TIME DESC
        """).fetchall()
        latest_runs = {}
        for r in run_rows:
            jid = r[0]
            if jid not in latest_runs:
                latest_runs[jid] = {
                    "job_id": r[0],
                    "stage": r[1],
                    "status": r[2],
                    "start_time": str(r[3]),
                    "end_time": str(r[4]),
                    "duration_sec": float(r[5]) if r[5] is not None else 0.0,
                    "rows_loaded": int(r[6]) if r[6] is not None else 0,
                    "error_message": r[7],
                }

        return edges_rows, trust_map, all_alerts, latest_runs

    finally:
        if should_close and conn:
            conn.close()


def _matches_target(target_obj: str, node_id: str, label: str) -> bool:
    """Robustly matches target_object from alert to node id or label."""
    t = target_obj.replace("OPSLENS.", "").strip().lower()
    nid = node_id.lower()
    lbl = label.lower()
    nid_stripped = nid.replace("tbl_", "").replace("job_", "").replace("mart_", "").replace("dash_", "").replace("feed_", "")
    return t in (nid, lbl, nid_stripped)


def get_lineage_graph(conn=None) -> Dict[str, Any]:
    """
    Returns complete lineage graph with nodes, directed edges, and computed blast radii.
    - Each node status is the worse of (trust-score status, highest alert severity).
    - Degraded nodes include active_alerts, inherited_from alerts, and a blast_radius object.
    """
    edges_rows, trust_map, all_alerts, latest_runs = fetch_lineage_data(conn)

    nodes_dict: Dict[str, Dict[str, Any]] = {}
    edges_list: List[Dict[str, Any]] = []
    downstream_adj: Dict[str, List[str]] = defaultdict(list)
    upstream_adj: Dict[str, List[str]] = defaultdict(list)

    # 1. Collect all nodes and edges
    for r in edges_rows:
        edge_id, src_id, src_type, src_lbl, tgt_id, tgt_type, tgt_lbl, rel_type = r

        downstream_adj[src_id].append(tgt_id)
        upstream_adj[tgt_id].append(src_id)

        if src_id not in nodes_dict:
            nodes_dict[src_id] = {
                "id": src_id,
                "label": src_lbl,
                "type": src_type.lower(),
            }

        if tgt_id not in nodes_dict:
            nodes_dict[tgt_id] = {
                "id": tgt_id,
                "label": tgt_lbl,
                "type": tgt_type.lower(),
            }

        edges_list.append({
            "edge_id": edge_id,
            "source": src_id,
            "target": tgt_id,
            "relation": rel_type,
            "relation_type": rel_type,
        })

    # 2. Attach direct active alerts to nodes
    for nid, node in nodes_dict.items():
        lbl = node["label"]
        matched_alerts = [a for a in all_alerts if _matches_target(a["target_object"], nid, lbl)]
        node["active_alerts"] = matched_alerts

    # 3. Compute inherited alerts for downstream nodes (BFS upstream)
    for nid, node in nodes_dict.items():
        inherited = []
        visited_up = set()
        queue = deque([nid])

        while queue:
            curr = queue.popleft()
            for parent_id in upstream_adj.get(curr, []):
                if parent_id not in visited_up:
                    visited_up.add(parent_id)
                    queue.append(parent_id)
                    parent_node = nodes_dict.get(parent_id, {})
                    for pa in parent_node.get("active_alerts", []):
                        inherited.append({
                            "source_node_id": parent_id,
                            "source_label": parent_node.get("label", parent_id),
                            "source_type": parent_node.get("type", "unknown"),
                            "alert_id": pa["alert_id"],
                            "incident_type": pa["incident_type"],
                            "severity": pa["severity"],
                            "summary": pa["summary"],
                            "suggested_root_cause": pa.get("suggested_root_cause"),
                            "recommended_action": pa.get("recommended_action"),
                        })
        node["inherited_from"] = inherited

    # 4. Attach trust scores, component scores, job metadata, and compute displayed status
    for nid, node in nodes_dict.items():
        lbl = node["label"]
        ntype = node["type"]

        clean_id = nid.replace("tbl_", "").replace("job_", "").replace("mart_", "").replace("dash_", "").replace("feed_", "")
        trust_info = trust_map.get(lbl) or trust_map.get(nid) or trust_map.get(clean_id) or {
            "trust_score": 100.0,
            "freshness_score": 100.0,
            "completeness_score": 100.0,
            "uniqueness_score": 100.0,
            "consistency_score": 100.0,
            "status": "GREEN",
        }

        node["trust_score"] = trust_info["trust_score"]
        node["component_scores"] = {
            "freshness": trust_info["freshness_score"],
            "completeness": trust_info["completeness_score"],
            "uniqueness": trust_info["uniqueness_score"],
            "consistency": trust_info["consistency_score"],
        }

        if ntype == "job":
            job_name = lbl
            node["last_run"] = latest_runs.get(job_name)

        # Worse of: (trust-score status, highest alert severity)
        all_node_alerts = node["active_alerts"] + node["inherited_from"]
        has_critical = any(a.get("severity") == "CRITICAL" for a in all_node_alerts)
        has_warning = any(a.get("severity") == "WARNING" for a in all_node_alerts)

        if trust_info["status"] == "RED" or node["trust_score"] < 70.0 or has_critical:
            displayed_status = "RED"
        elif trust_info["status"] == "AMBER" or node["trust_score"] < 85.0 or has_warning:
            displayed_status = "AMBER"
        else:
            displayed_status = "GREEN"

        node["status"] = displayed_status

    # 5. Compute blast radius for degraded nodes or nodes with open alerts
    banner_blasts = []
    for nid, node in nodes_dict.items():
        has_alerts = len(node["active_alerts"]) > 0
        is_degraded = node["status"] != "GREEN" or node["trust_score"] < 85.0

        if has_alerts or is_degraded:
            # BFS downstream traversal
            visited_down = set()
            q_down = deque([nid])
            by_type = {"table": [], "mart": [], "dashboard": [], "job": []}
            affected_ids = []

            while q_down:
                curr = q_down.popleft()
                for child_id in downstream_adj.get(curr, []):
                    if child_id not in visited_down:
                        visited_down.add(child_id)
                        q_down.append(child_id)
                        affected_ids.append(child_id)
                        c_meta = nodes_dict.get(child_id, {})
                        c_type = c_meta.get("type", "").lower()
                        if c_type in by_type:
                            by_type[c_type].append(child_id)
                        else:
                            by_type.setdefault(c_type, []).append(child_id)

            n_tables = len(by_type.get("table", []))
            m_marts = len(by_type.get("mart", []))
            k_dashboards = len(by_type.get("dashboard", []))
            summary_str = f"Failure in {node['label']} affects {n_tables} tables, {m_marts} marts and {k_dashboards} dashboards"

            node["blast_radius"] = {
                "summary": summary_str,
                "affected_count": len(affected_ids),
                "affected_node_ids": affected_ids,
                "by_type": by_type,
            }

            if has_alerts:
                banner_blasts.append({
                    "node_id": nid,
                    "label": node["label"],
                    "summary": summary_str,
                    "affected_node_ids": affected_ids,
                })
        else:
            node["blast_radius"] = None

    return {
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
        "total_nodes": len(nodes_dict),
        "total_edges": len(edges_list),
        "banner_blast": banner_blasts[0] if banner_blasts else None,
    }


def get_blast_radius(node_id: str, conn=None) -> Dict[str, Any]:
    """
    Performs breadth-first traversal from node_id along downstream edges
    to determine all downstream tables, marts, and dashboards impacted.
    Also traverses upstream to find root source dependencies.
    """
    edges_rows, trust_map, all_alerts, latest_runs = fetch_lineage_data(conn)

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
                child_meta["type"] = child_meta["type"].lower()
                affected_nodes.append(child_meta)
                if child_meta["type"] == "dashboard":
                    affected_dashboards.append(child_meta["label"])
                elif child_meta["type"] == "mart":
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
