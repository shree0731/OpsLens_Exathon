/**
 * Real OpsLens API JSON Schema Types
 * Based on responses from backend endpoints:
 * /api/lineage, /api/trust, /api/alerts, /api/timeline, /api/runs, /api/faults/status, /api/health
 */

export type StatusLevel = 'GREEN' | 'AMBER' | 'RED';
export type SeverityLevel = 'CRITICAL' | 'WARNING' | 'INFO';

export type NodeType = 'source' | 'job' | 'table' | 'mart' | 'dashboard';

export interface ComponentScores {
  freshness: number;
  completeness: number;
  uniqueness: number;
  consistency: number;
}

export interface NodeAlert {
  alert_id: string;
  incident_type: string;
  severity: SeverityLevel;
  summary: string;
  details?: string;
  suggested_root_cause?: string;
  recommended_action?: string;
  first_seen?: string;
}

export interface InheritedAlert {
  source_node_id: string;
  source_label: string;
  source_type: string;
  alert_id: string;
  incident_type: string;
  severity: SeverityLevel;
  summary: string;
  suggested_root_cause?: string;
  recommended_action?: string;
}

export interface BlastRadiusByType {
  table: string[];
  mart: string[];
  dashboard: string[];
  job: string[];
}

export interface BlastRadius {
  summary: string;
  affected_count: number;
  affected_node_ids: string[];
  by_type: BlastRadiusByType;
}

export interface JobLastRun {
  job_id: string;
  stage: string;
  status: string;
  start_time: string;
  end_time: string;
  duration_sec: number;
  rows_loaded: number;
  error_message?: string | null;
}

export interface LineageNode {
  id: string;
  label: string;
  type: NodeType;
  trust_score: number;
  status: StatusLevel;
  active_alerts: NodeAlert[];
  inherited_from: InheritedAlert[];
  component_scores?: ComponentScores;
  last_run?: JobLastRun;
  blast_radius?: BlastRadius | null;
}

export interface LineageEdge {
  edge_id: string;
  source: string;
  target: string;
  relation: string;
  relation_type?: string;
}

export interface BannerBlast {
  node_id: string;
  label: string;
  summary: string;
  affected_node_ids: string[];
}

export interface LineageGraphResponse {
  nodes: LineageNode[];
  edges: LineageEdge[];
  total_nodes: number;
  total_edges: number;
  banner_blast?: BannerBlast | null;
}

export interface HealthResponse {
  status: string;
  app: string;
  database: string;
  exasol_version: string;
  reference_clock: string;
  open_alerts_count: number;
  average_trust_score: number;
  timestamp: string;
}

export interface TrustScoreItem {
  object_name: string;
  object_type: string;
  trust_score: number;
  freshness_score: number;
  completeness_score: number;
  uniqueness_score: number;
  consistency_score: number;
  status: StatusLevel;
  computed_at: string;
}

export interface TrustHistoryItem {
  object_name: string;
  trust_score: number;
  freshness_score: number;
  completeness_score: number;
  uniqueness_score: number;
  consistency_score: number;
  computed_at: string;
}

export interface AlertItem {
  alert_id: string;
  incident_type: string;
  severity: SeverityLevel;
  target_object: string;
  summary: string;
  details: string;
  suggested_root_cause: string;
  recommended_action: string;
  status: string;
  first_seen: string;
  last_seen: string;
}

export interface ActiveFaultItem {
  fault_id: string;
  fault_name: string;
  target_table: string;
  details: string;
  status: string;
  injected_at: string;
  cleared_at?: string | null;
}

export interface FaultStatusResponse {
  active_faults_count: number;
  active_faults: ActiveFaultItem[];
  recent_history: ActiveFaultItem[];
}

export interface FaultInjectionResponse {
  fault: string;
  status: string;
  new_alerts_count: number;
  new_alerts: Array<{
    alert_id: string;
    incident_type: string;
    severity: string;
    summary: string;
  }>;
  affected_objects: Array<{
    object_name: string;
    trust_score: number;
    status: StatusLevel;
  }>;
  blast_radius?: {
    target_node: { id: string };
    impact_summary: string;
    affected_count: number;
    affected_dashboards: string[];
    affected_marts: string[];
  };
}

export interface PipelineRunItem {
  run_id: string;
  batch_id: string;
  job_id: string;
  stage: string;
  start_time: string;
  end_time: string;
  duration_sec: number;
  status: string;
  rows_loaded: number;
  error_message?: string | null;
  is_simulated: boolean;
}

export interface TimelineEventItem {
  event_id: string;
  event_type: 'PIPELINE_RUN' | 'SENTINEL_CHECK' | 'ALERT_OPEN' | 'ALERT_RESOLVED' | 'FAULT_INJECTION';
  category: string;
  severity: string;
  title: string;
  description: string;
  event_timestamp: string;
}
