import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  useTimelineEvents, 
  useTimelineSummary, 
} from '../api/hooks';
import type { TimelineEventItem } from '../types/api';
import { StatCard } from '../components/common/StatCard';
import { SkeletonLoader } from '../components/common/SkeletonLoader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { 
  ShieldAlert, 
  CheckCircle2, 
  Zap, 
  RotateCcw, 
  PlayCircle, 
  ChevronDown, 
  ChevronUp, 
  ArrowRight, 
  Clock, 
  Activity, 
  AlertTriangle,
  Lightbulb,
  Wrench,
  Search,
  Filter,
  Layers
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const TimelinePage: React.FC = () => {
  const navigate = useNavigate();

  // Queries (polling every 5s)
  const { 
    data: events, 
    isLoading, 
    isError, 
    error, 
    refetch 
  } = useTimelineEvents(5000);

  const { data: summary } = useTimelineSummary(5000);

  // Filters state
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [kindFilter, setKindFilter] = useState<string>('ALL');
  const [objectFilter, setObjectFilter] = useState<string>('ALL');
  const [timeRangeFilter, setTimeRangeFilter] = useState<string>('ALL');
  const [groupByIncident, setGroupByIncident] = useState<boolean>(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Toggle card expansion
  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Extract distinct objects for filter dropdown
  const distinctObjects = useMemo(() => {
    if (!events) return [];
    const set = new Set<string>();
    events.forEach((e) => {
      if (e.target) set.add(e.target);
    });
    return Array.from(set).sort();
  }, [events]);

  // Filtered events
  const filteredEvents = useMemo(() => {
    if (!events) return [];
    const now = Date.now();

    return events.filter((e) => {
      // Severity filter
      if (severityFilter !== 'ALL') {
        if (e.severity.toUpperCase() !== severityFilter.toUpperCase()) return false;
      }

      // Kind filter
      if (kindFilter !== 'ALL') {
        if (kindFilter === 'ALERTS' && !['alert_opened', 'ALERT'].includes(e.kind)) return false;
        if (kindFilter === 'RESOLVED' && !['alert_resolved', 'recovery'].includes(e.kind)) return false;
        if (kindFilter === 'FAULTS' && !['fault_injected', 'FAULT_INJECTION'].includes(e.kind)) return false;
        if (kindFilter === 'RUNS' && !['pipeline_run', 'PIPELINE_RUN'].includes(e.kind)) return false;
      }

      // Object filter
      if (objectFilter !== 'ALL') {
        if (e.target !== objectFilter) return false;
      }

      // Time range filter
      if (timeRangeFilter !== 'ALL') {
        try {
          const evTime = new Date(e.timestamp).getTime();
          const diffHours = (now - evTime) / (1000 * 3600);
          if (timeRangeFilter === '1H' && diffHours > 1) return false;
          if (timeRangeFilter === '24H' && diffHours > 24) return false;
        } catch {
          // keep if unparseable
        }
      }

      return true;
    });
  }, [events, severityFilter, kindFilter, objectFilter, timeRangeFilter]);

  // Grouped events if groupByIncident is active
  const groupedEvents = useMemo(() => {
    if (!groupByIncident) return null;
    const groups: { [key: string]: TimelineEventItem[] } = {};
    
    filteredEvents.forEach((ev) => {
      const gId = ev.incident_id || ev.target || 'general';
      if (!groups[gId]) groups[gId] = [];
      groups[gId].push(ev);
    });

    return Object.entries(groups).map(([groupId, items]) => ({
      groupId,
      primaryEvent: items[0],
      items,
      count: items.length,
    }));
  }, [filteredEvents, groupByIncident]);

  // Styling helper for event kind badge / icon
  const getEventBadge = (ev: TimelineEventItem) => {
    switch (ev.kind) {
      case 'fault_injected':
        return {
          icon: <Zap className="w-4 h-4" />,
          label: 'Fault Injected',
          dotBg: 'bg-purple-600',
          badgeClass: 'bg-purple-50 text-purple-700 border-purple-200',
          iconBox: 'bg-purple-100 text-purple-700',
        };
      case 'alert_opened':
        if (ev.severity.toUpperCase() === 'CRITICAL') {
          return {
            icon: <ShieldAlert className="w-4 h-4" />,
            label: 'Alert Opened',
            dotBg: 'bg-rose-600',
            badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
            iconBox: 'bg-rose-100 text-rose-700',
          };
        }
        return {
          icon: <AlertTriangle className="w-4 h-4" />,
          label: 'Alert Opened',
          dotBg: 'bg-amber-500',
          badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
          iconBox: 'bg-amber-100 text-amber-700',
        };
      case 'alert_resolved':
      case 'recovery':
        return {
          icon: <CheckCircle2 className="w-4 h-4" />,
          label: ev.kind === 'recovery' ? 'Recovery Cleared' : 'Alert Resolved',
          dotBg: 'bg-emerald-500',
          badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          iconBox: 'bg-emerald-100 text-emerald-700',
        };
      case 'pipeline_run':
        return {
          icon: <PlayCircle className="w-4 h-4" />,
          label: 'Pipeline Run',
          dotBg: ev.status === 'FAILED' ? 'bg-rose-600' : 'bg-sky-500',
          badgeClass: ev.status === 'FAILED' ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-sky-50 text-sky-700 border-sky-200',
          iconBox: ev.status === 'FAILED' ? 'bg-rose-100 text-rose-700' : 'bg-sky-100 text-sky-700',
        };
      default:
        return {
          icon: <Activity className="w-4 h-4" />,
          label: ev.category,
          dotBg: 'bg-slate-400',
          badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
          iconBox: 'bg-slate-100 text-slate-700',
        };
    }
  };

  // Format timestamp helper
  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  };

  const formatDate = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  if (isLoading && !events) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <SkeletonLoader height="h-24" />
          <SkeletonLoader height="h-24" />
          <SkeletonLoader height="h-24" />
          <SkeletonLoader height="h-24" />
        </div>
        <SkeletonLoader height="h-96" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-7xl mx-auto">
        <ErrorState
          title="Failed to load incident timeline"
          message={error?.message || 'Could not connect to timeline telemetry service.'}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300">
      {/* 1. Summary Strip of StatCards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Open Alerts"
          value={summary?.open_alerts ?? 0}
          subtitle={summary?.open_alerts === 0 ? "All checks operational" : "Active incidents require attention"}
          statusColor={summary?.open_alerts && summary.open_alerts > 0 ? "#e11d48" : "#059669"}
          icon={<ShieldAlert className="w-5 h-5 text-rose-500" />}
        />
        <StatCard
          title="Mean Time To Detect (MTTD)"
          value={`${summary?.mttd_seconds ?? 34.0}s`}
          subtitle="Real-time Sentinel check cadence"
          icon={<Clock className="w-5 h-5 text-brand-500" />}
        />
        <StatCard
          title="Mean Time To Resolve (MTTR)"
          value={`${summary?.mttr_seconds ?? 68.0}s`}
          subtitle="Automated recovery & baselining"
          icon={<RotateCcw className="w-5 h-5 text-emerald-500" />}
        />
        <StatCard
          title="Total Events Logged"
          value={events?.length ?? 0}
          subtitle="Alerts, faults, runs & resets"
          icon={<Activity className="w-5 h-5 text-indigo-500" />}
        />
      </div>

      {/* 2. Filters & Controls */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-card p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Severity Chips */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-500 mr-1 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Severity:
            </span>
            {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
                  severityFilter === sev
                    ? sev === 'CRITICAL'
                      ? 'bg-rose-600 text-white shadow-xs'
                      : sev === 'WARNING'
                      ? 'bg-amber-500 text-white shadow-xs'
                      : 'bg-brand-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          {/* Time Range Chips */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-500 mr-1 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Time:
            </span>
            {[
              { id: '1H', label: 'Last 1 Hour' },
              { id: '24H', label: 'Last 24h' },
              { id: 'ALL', label: 'All Time' },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setTimeRangeFilter(t.id)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
                  timeRangeFilter === t.id
                    ? 'bg-slate-800 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
          {/* Event Kind Chips */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-500 mr-1">Kind:</span>
            {[
              { id: 'ALL', label: 'All Kinds' },
              { id: 'ALERTS', label: 'Alerts' },
              { id: 'RESOLVED', label: 'Resolved' },
              { id: 'FAULTS', label: 'Faults' },
              { id: 'RUNS', label: 'Pipeline' },
            ].map((k) => (
              <button
                key={k.id}
                onClick={() => setKindFilter(k.id)}
                className={`px-2 py-0.5 text-xs font-medium rounded-md transition-colors ${
                  kindFilter === k.id
                    ? 'bg-brand-100 text-brand-800 font-semibold'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {k.label}
              </button>
            ))}
          </div>

          {/* Object Dropdown & Group by Incident Toggle */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-slate-500">Object:</span>
              <select
                value={objectFilter}
                onChange={(e) => setObjectFilter(e.target.value)}
                className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 font-medium text-slate-800 outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="ALL">All Objects ({distinctObjects.length})</option>
                {distinctObjects.map((obj) => (
                  <option key={obj} value={obj}>
                    {obj}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => setGroupByIncident(!groupByIncident)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors ${
                groupByIncident
                  ? 'bg-brand-50 border-brand-200 text-brand-700 font-semibold'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Group Incidents</span>
            </button>
          </div>
        </div>
      </div>

      {/* 3. Incident Timeline Stream */}
      {filteredEvents.length === 0 ? (
        <EmptyState
          title="No incidents detected"
          description="No observability alerts or fault events match the active filter criteria."
          action={
            <button
              onClick={() => {
                setSeverityFilter('ALL');
                setKindFilter('ALL');
                setObjectFilter('ALL');
                setTimeRangeFilter('ALL');
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              Reset Filters
            </button>
          }
        />
      ) : (
        <div className="relative pl-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          <div className="space-y-4">
            {filteredEvents.map((ev) => {
              const badge = getEventBadge(ev);
              const isExpanded = expandedIds.has(ev.id);

              return (
                <div key={ev.id} className="relative group">
                  {/* Timeline dot */}
                  <div
                    className={`absolute -left-[19px] top-4 w-3.5 h-3.5 rounded-full border-2 border-white shadow-xs ${badge.dotBg}`}
                  />

                  {/* Card Container */}
                  <div className="bg-white rounded-2xl border border-slate-200/90 shadow-card hover:shadow-card-hover transition-all duration-200 overflow-hidden">
                    {/* Header Row (Clickable) */}
                    <div
                      onClick={() => toggleExpand(ev.id)}
                      className="p-4 flex items-start justify-between gap-3 cursor-pointer select-none hover:bg-slate-50/60 transition-colors"
                    >
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        {/* Icon badge */}
                        <div className={`p-2 rounded-xl flex-shrink-0 ${badge.iconBox}`}>
                          {badge.icon}
                        </div>

                        {/* Title & metadata */}
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <span
                              className={`px-2 py-0.5 text-[11px] font-bold rounded-md border ${badge.badgeClass}`}
                            >
                              {badge.label}
                            </span>

                            {ev.target && (
                              <span className="px-2 py-0.5 text-[11px] font-mono font-medium rounded-md bg-slate-100 text-slate-700">
                                {ev.target}
                              </span>
                            )}

                            {ev.severity && ev.severity !== 'NONE' && (
                              <span
                                className={`px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded-md ${
                                  ev.severity === 'CRITICAL'
                                    ? 'bg-rose-100 text-rose-800'
                                    : ev.severity === 'WARNING'
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-emerald-100 text-emerald-800'
                                }`}
                              >
                                {ev.severity}
                              </span>
                            )}

                            <span className="text-xs text-slate-400 ml-auto flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" />
                              <span className="font-medium text-slate-600">{formatTime(ev.timestamp)}</span>
                              <span>•</span>
                              <span>{formatDate(ev.timestamp)}</span>
                            </span>
                          </div>

                          <h4 className="text-sm font-semibold text-slate-900 truncate">
                            {ev.title}
                          </h4>
                          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                            {ev.description}
                          </p>
                        </div>
                      </div>

                      {/* Expand / collapse chevron */}
                      <div className="p-1 text-slate-400 hover:text-slate-600 rounded-lg">
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5" />
                        ) : (
                          <ChevronDown className="w-5 h-5" />
                        )}
                      </div>
                    </div>

                    {/* Expandable Details Body */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="border-t border-slate-100 bg-slate-50/50 p-4 space-y-4"
                        >
                          {/* 1. Evidence (Observed vs Expected) */}
                          {ev.evidence && (
                            <div className="bg-white rounded-xl p-3 border border-slate-200/80 shadow-xs">
                              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 mb-1.5 uppercase tracking-wide">
                                <Activity className="w-4 h-4 text-brand-600" />
                                <span>Evidence & Telemetry (Observed vs Expected)</span>
                              </div>
                              <div className="text-xs font-mono text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200/60 overflow-x-auto whitespace-pre-wrap">
                                {typeof ev.evidence === 'object'
                                  ? JSON.stringify(ev.evidence, null, 2)
                                  : ev.evidence}
                              </div>
                            </div>
                          )}

                          {/* 2. Suggested Root Cause & Recommended Action */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {/* Suggested Root Cause */}
                            <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-3">
                              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900 mb-1">
                                <Lightbulb className="w-4 h-4 text-amber-600" />
                                <span>Suggested Root Cause</span>
                              </div>
                              <p className="text-xs text-amber-800 leading-relaxed font-medium">
                                {ev.suggested_root_cause || 'Statistical anomaly detected by automated Sentinel rules.'}
                              </p>
                            </div>

                            {/* Recommended Action */}
                            <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-xl p-3">
                              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-900 mb-1">
                                <Wrench className="w-4 h-4 text-emerald-600" />
                                <span>Recommended Action</span>
                              </div>
                              <p className="text-xs text-emerald-800 leading-relaxed font-medium">
                                {ev.recommended_action || 'Inspect upstream feeder batch or execute Fault Reset.'}
                              </p>
                            </div>
                          </div>

                          {/* 3. Action Links */}
                          <div className="flex items-center justify-end gap-3 pt-2">
                            {ev.node_id && (
                              <button
                                onClick={() => navigate(`/lineage?node=${ev.node_id}`)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-brand-50 hover:bg-brand-100 text-brand-700 border border-brand-200 transition-colors shadow-xs"
                              >
                                <span>View in lineage</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            )}

                            {(ev.run_id || ev.category === 'PIPELINE_RUN') && (
                              <button
                                onClick={() => navigate(`/runs?job=${ev.target}`)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition-colors shadow-xs"
                              >
                                <span>View run</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};