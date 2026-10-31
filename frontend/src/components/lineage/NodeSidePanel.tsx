import React from 'react';
import { SidePanel } from '../common/SidePanel';
import { StatusBadge } from '../common/StatusBadge';
import { TrustRing } from '../common/TrustRing';
import { useTrustHistory } from '../../api/hooks';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip 
} from 'recharts';
import { 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight, 
  ArrowDownRight, 
  HelpCircle, 
  Activity, 
  Zap, 
  ShieldCheck 
} from 'lucide-react';
import type { LineageNode } from '../../types/api';

interface NodeSidePanelProps {
  node: LineageNode | null;
  onClose: () => void;
  onSelectNode?: (nodeId: string) => void;
  upstreamNodes?: Array<{ id: string; label: string; type: string }>;
  downstreamNodes?: Array<{ id: string; label: string; type: string }>;
}

export const NodeSidePanel: React.FC<NodeSidePanelProps> = ({
  node,
  onClose,
  onSelectNode,
  upstreamNodes = [],
  downstreamNodes = [],
}) => {
  if (!node) return null;

  const { data: history = [] } = useTrustHistory(node.label, 14);

  const scores = node.component_scores || {
    freshness: 100.0,
    completeness: 100.0,
    uniqueness: 100.0,
    consistency: 100.0,
  };

  const chartData = (history || []).map((h) => ({
    date: h.computed_at ? h.computed_at.slice(5, 16) : '',
    score: h.trust_score,
  }));

  const allAlerts = node.active_alerts || [];
  const inheritedAlerts = node.inherited_from || [];

  return (
    <SidePanel
      isOpen={!!node}
      onClose={onClose}
      title={node.label}
      subtitle={`Node ID: ${node.id} • Type: ${node.type.toUpperCase()}`}
      width="w-[450px]"
    >
      {/* 1. Overall Trust Score & Status */}
      <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrustRing
            score={node.trust_score}
            status={node.status}
            size={52}
            strokeWidth={4.5}
          />
          <div>
            <p className="text-xs text-slate-500 font-medium">Reliability Trust Score</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xl font-bold text-slate-900">{node.trust_score.toFixed(1)}%</span>
              <StatusBadge status={node.status} size="sm" />
            </div>
          </div>
        </div>
      </div>

      {/* 2. Four Component Trust Scores */}
      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-slate-400" />
          Component Breakdown
        </h4>
        <div className="space-y-2.5 bg-white rounded-xl p-3.5 border border-slate-100 shadow-soft">
          {[
            { name: 'Freshness (30%)', score: scores.freshness, color: 'bg-blue-500' },
            { name: 'Completeness (20%)', score: scores.completeness, color: 'bg-emerald-500' },
            { name: 'Uniqueness (20%)', score: scores.uniqueness, color: 'bg-indigo-500' },
            { name: 'Consistency (30%)', score: scores.consistency, color: 'bg-amber-500' },
          ].map((c) => (
            <div key={c.name} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-600 font-medium">{c.name}</span>
                <span className="font-bold text-slate-900">{c.score.toFixed(1)}%</span>
              </div>
              <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${c.color} transition-all duration-500`}
                  style={{ width: `${Math.max(0, Math.min(100, c.score))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Trust Trend Sparkline */}
      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          Historical Trust Trend (14 Days)
        </h4>
        <div className="bg-white rounded-xl p-3 border border-slate-100 shadow-soft h-36">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis domain={[50, 100]} hide />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-slate-900 text-white text-xs px-2.5 py-1.5 rounded-lg shadow-md">
                          <p className="font-semibold">{payload[0].value}%</p>
                          <p className="text-[10px] text-slate-300">{payload[0].payload.date}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  dot={{ r: 2, fill: '#3B82F6' }}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No historical trend available
            </div>
          )}
        </div>
      </div>

      {/* 4. Active Alerts & Root Cause Analysis */}
      {allAlerts.length > 0 && (
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-rose-500 mb-3 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5" />
            Direct Open Incidents ({allAlerts.length})
          </h4>
          <div className="space-y-3">
            {allAlerts.map((alt) => (
              <div
                key={alt.alert_id}
                className="bg-rose-50/60 border border-rose-200/80 rounded-xl p-3.5 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-950">{alt.incident_type}</span>
                  <StatusBadge status={alt.severity} size="sm" />
                </div>
                <p className="text-slate-800 font-medium">{alt.summary}</p>
                {alt.suggested_root_cause && (
                  <div className="bg-white/80 rounded-lg p-2 border border-rose-100 text-[11px] text-slate-700">
                    <span className="font-semibold text-rose-900">Root Cause: </span>
                    {alt.suggested_root_cause}
                  </div>
                )}
                {alt.recommended_action && (
                  <div className="bg-white/80 rounded-lg p-2 border border-slate-100 text-[11px] text-slate-700">
                    <span className="font-semibold text-slate-900">Suggested Action: </span>
                    {alt.recommended_action}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Inherited Upstream Alerts */}
      {inheritedAlerts.length > 0 && (
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-600 mb-3 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5" />
            Degraded by Upstream Dependencies ({inheritedAlerts.length})
          </h4>
          <div className="space-y-3">
            {inheritedAlerts.map((inh, idx) => (
              <div
                key={`${inh.alert_id}-${idx}`}
                className="bg-amber-50/60 border border-amber-200/80 rounded-xl p-3.5 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-amber-950">
                    Upstream: {inh.source_label} ({inh.source_type})
                  </span>
                  <StatusBadge status={inh.severity} size="sm" />
                </div>
                <p className="text-slate-800 font-medium">{inh.summary}</p>
                {inh.suggested_root_cause && (
                  <div className="bg-white/80 rounded-lg p-2 border border-amber-100 text-[11px] text-slate-700">
                    <span className="font-semibold text-amber-900">Upstream Cause: </span>
                    {inh.suggested_root_cause}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. Last Run Info (For Job Nodes) */}
      {node.type === 'job' && node.last_run && (
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            Latest Execution Telemetry
          </h4>
          <div className="bg-white rounded-xl p-3.5 border border-slate-100 shadow-soft text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-500">Stage:</span>
              <span className="font-semibold text-slate-800">{node.last_run.stage}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Status:</span>
              <StatusBadge status={node.last_run.status} size="sm" />
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Duration:</span>
              <span className="font-mono text-slate-800">{node.last_run.duration_sec.toFixed(1)}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Rows Loaded:</span>
              <span className="font-mono text-slate-800">{node.last_run.rows_loaded.toLocaleString()}</span>
            </div>
            {node.last_run.error_message && (
              <div className="mt-2 p-2 rounded-lg bg-rose-50 text-rose-700 text-[11px] font-mono border border-rose-200">
                {node.last_run.error_message}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 7. Upstream and Downstream Dependencies */}
      <div className="grid grid-cols-2 gap-3 pt-2">
        {/* Upstream */}
        <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
          <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
            <ArrowUpRight className="w-3 h-3 text-slate-400" />
            Upstream ({upstreamNodes.length})
          </p>
          <div className="space-y-1">
            {upstreamNodes.length > 0 ? (
              upstreamNodes.map((u) => (
                <button
                  key={u.id}
                  onClick={() => onSelectNode && onSelectNode(u.id)}
                  className="w-full text-left text-xs font-medium text-slate-700 hover:text-brand-600 truncate py-0.5 block hover:underline"
                >
                  {u.label}
                </button>
              ))
            ) : (
              <span className="text-xs text-slate-400">Source root</span>
            )}
          </div>
        </div>

        {/* Downstream */}
        <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
          <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
            <ArrowDownRight className="w-3 h-3 text-slate-400" />
            Downstream ({downstreamNodes.length})
          </p>
          <div className="space-y-1">
            {downstreamNodes.length > 0 ? (
              downstreamNodes.map((d) => (
                <button
                  key={d.id}
                  onClick={() => onSelectNode && onSelectNode(d.id)}
                  className="w-full text-left text-xs font-medium text-slate-700 hover:text-brand-600 truncate py-0.5 block hover:underline"
                >
                  {d.label}
                </button>
              ))
            ) : (
              <span className="text-xs text-slate-400">Terminal node</span>
            )}
          </div>
        </div>
      </div>
    </SidePanel>
  );
};
