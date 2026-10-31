import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  usePipelineRuns, 
  useRunsCalendar,
} from '../api/hooks';
import type { PipelineRunItem, DaySummaryItem } from '../types/api';
import { SidePanel } from '../components/common/SidePanel';
import { SkeletonLoader } from '../components/common/SkeletonLoader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  MinusCircle, 
  ChevronRight, 
  ChevronLeft, 
  Clock, 
  Layers, 
  Calendar, 
  Database, 
  ArrowRight,
  TrendingUp,
  AlertOctagon,
  Info
} from 'lucide-react';

const STAGE_ORDER = ['extract', 'load', 'validate', 'transform', 'publish'];

const JOBS_CONFIG = [
  { id: 'load_orders', name: 'Load Orders', target: 'ORDERS', category: 'Ingestion' },
  { id: 'load_lineitem', name: 'Load Line Items', target: 'LINEITEM', category: 'Ingestion' },
  { id: 'load_energy', name: 'Load Energy Meter Data', target: 'ENERGY_READINGS', category: 'Ingestion' },
  { id: 'load_weather', name: 'Load Weather Observations', target: 'WEATHER_DAILY', category: 'Ingestion' },
  { id: 'build_revenue_mart', name: 'Build Revenue Mart', target: 'REVENUE_MART', category: 'Transformation' },
  { id: 'publish_dashboards', name: 'Publish Dashboards', target: 'ALL_DASHBOARDS', category: 'Publishing' },
];

export const RunsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Selected date & job from searchParams or state
  const jobParam = searchParams.get('job') || 'ALL';
  const [selectedJob, setSelectedJob] = useState<string>(jobParam);

  // Calendar days query
  const { 
    data: calendarDays, 
    isLoading: isCalLoading, 
    isError: isCalError, 
    refetch: refetchCal 
  } = useRunsCalendar(14);

  // Default date: today or first day of calendar
  const [selectedDate, setSelectedDate] = useState<string>('2026-10-31');

  useEffect(() => {
    if (calendarDays && calendarDays.length > 0 && !calendarDays.some(c => c.date === selectedDate)) {
      setSelectedDate(calendarDays[0].date);
    }
  }, [calendarDays, selectedDate]);

  // Sync selectedJob with URL
  useEffect(() => {
    if (jobParam !== selectedJob) {
      setSelectedJob(jobParam);
    }
  }, [jobParam]);

  // Fetch runs for the selected date
  const { 
    data: runs, 
    isLoading: isRunsLoading, 
    isError: isRunsError, 
    refetch: refetchRuns 
  } = usePipelineRuns({ date: selectedDate }, 5000);

  // Active selected stage for SidePanel
  const [selectedStageData, setSelectedStageData] = useState<{
    jobId: string;
    jobName: string;
    stage: string;
    run?: PipelineRunItem;
    status: 'SUCCESS' | 'WARNING' | 'FAILED' | 'SKIPPED';
  } | null>(null);

  // Day summary calculation
  const currentDayStats = useMemo(() => {
    if (!calendarDays) return null;
    return calendarDays.find((d) => d.date === selectedDate) || null;
  }, [calendarDays, selectedDate]);

  // Filter jobs based on selectedJob dropdown
  const filteredJobs = useMemo(() => {
    if (selectedJob === 'ALL') return JOBS_CONFIG;
    return JOBS_CONFIG.filter((j) => j.id === selectedJob);
  }, [selectedJob]);

  // Group runs by job_id and stage
  const runsByJobAndStage = useMemo(() => {
    const map = new Map<string, PipelineRunItem>();
    if (!runs) return map;
    runs.forEach((r) => {
      // Key: job_id:stage
      map.set(`${r.job_id}:${r.stage}`, r);
    });
    return map;
  }, [runs]);

  // Handle stage click
  const handleStageClick = (
    jobId: string, 
    jobName: string, 
    stage: string, 
    run?: PipelineRunItem, 
    computedStatus: 'SUCCESS' | 'WARNING' | 'FAILED' | 'SKIPPED' = 'SUCCESS'
  ) => {
    setSelectedStageData({
      jobId,
      jobName,
      stage,
      run,
      status: computedStatus,
    });
  };

  if (isCalLoading && !calendarDays) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <SkeletonLoader height="h-20" />
        <SkeletonLoader height="h-32" />
        <SkeletonLoader height="h-96" />
      </div>
    );
  }

  if (isCalError || isRunsError) {
    return (
      <div className="max-w-7xl mx-auto">
        <ErrorState
          title="Failed to load pipeline runs"
          message="Could not retrieve execution telemetry for the specified date."
          onRetry={() => {
            refetchCal();
            refetchRuns();
          }}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300">
      {/* 1. Top Summary Banner */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-card p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Pipeline Execution Workflow
            </h2>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[11px] font-semibold border border-slate-200">
              <Info className="w-3.5 h-3.5 text-slate-500" />
              Simulated run history
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Overnight 5-stage telemetry across 6 production jobs with statistical baseline SLA tracking.
          </p>
        </div>

        {/* Day Metric Counters */}
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-2 rounded-xl bg-emerald-50 border border-emerald-200/80 text-center min-w-[80px]">
            <div className="text-lg font-bold text-emerald-700">
              {currentDayStats?.succeeded_jobs ?? 6}
            </div>
            <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wide">
              Succeeded
            </div>
          </div>

          <div className="px-3.5 py-2 rounded-xl bg-amber-50 border border-amber-200/80 text-center min-w-[80px]">
            <div className="text-lg font-bold text-amber-700">
              {currentDayStats?.late_jobs ?? 0}
            </div>
            <div className="text-[10px] font-bold text-amber-600 uppercase tracking-wide">
              Late / SLA
            </div>
          </div>

          <div className="px-3.5 py-2 rounded-xl bg-rose-50 border border-rose-200/80 text-center min-w-[80px]">
            <div className="text-lg font-bold text-rose-700">
              {currentDayStats?.failed_jobs ?? 0}
            </div>
            <div className="text-[10px] font-bold text-rose-600 uppercase tracking-wide">
              Failed
            </div>
          </div>

          <div className="hidden sm:block px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-center min-w-[90px]">
            <div className="text-lg font-bold text-slate-800">
              {(currentDayStats?.total_rows ?? 0).toLocaleString()}
            </div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
              Total Rows
            </div>
          </div>
        </div>
      </div>

      {/* 2. Day Picker (14 Days) & Job Selector */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-card p-4 space-y-4">
        {/* Day Strip */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-brand-600" />
              Select Date (Last 14 Days)
            </span>
            <span className="text-xs text-slate-400">
              Showing runs for <span className="font-semibold text-slate-700">{selectedDate}</span>
            </span>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
            {(calendarDays || []).map((day) => {
              const isSelected = day.date === selectedDate;
              const dotColor = 
                day.status === 'failed' 
                  ? 'bg-rose-500' 
                  : day.status === 'warning' 
                  ? 'bg-amber-500' 
                  : 'bg-emerald-500';

              return (
                <button
                  key={day.date}
                  onClick={() => setSelectedDate(day.date)}
                  className={`flex-shrink-0 flex flex-col items-center justify-center px-3.5 py-2 rounded-xl border transition-all text-xs ${
                    isSelected
                      ? 'bg-brand-50 border-brand-500 text-brand-900 shadow-sm ring-1 ring-brand-500'
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-0.5">
                    {day.day_of_week}
                  </span>
                  <div className="flex items-center gap-1.5 font-bold">
                    <span>{day.display_date}</span>
                    <span className={`w-2 h-2 rounded-full ${dotColor}`} />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Job Filter Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Filter Job:</span>
            <select
              value={selectedJob}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedJob(val);
                setSearchParams((prev) => {
                  if (val === 'ALL') prev.delete('job');
                  else prev.set('job', val);
                  return prev;
                });
              }}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-800 outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="ALL">All Jobs ({JOBS_CONFIG.length})</option>
              {JOBS_CONFIG.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.name} ({j.id})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Success
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Late / Slow
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Failed
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-300" /> Skipped
            </span>
          </div>
        </div>
      </div>

      {/* 3. Horizontal Lanes for each Job */}
      <div className="space-y-6">
        {filteredJobs.map((job) => (
          <JobWorkflowLane
            key={job.id}
            job={job}
            runsByJobAndStage={runsByJobAndStage}
            onStageClick={handleStageClick}
          />
        ))}
      </div>

      {/* 4. SidePanel Details for Clicked Stage */}
      <SidePanel
        isOpen={!!selectedStageData}
        onClose={() => setSelectedStageData(null)}
        title={selectedStageData ? `${selectedStageData.jobName} — ${selectedStageData.stage.toUpperCase()}` : ''}
        subtitle="Stage execution telemetry, SLA baseline comparison, and root cause link"
        width="w-[460px]"
      >
        {selectedStageData && (
          <StageDetailPanelContent
            jobId={selectedStageData.jobId}
            jobName={selectedStageData.jobName}
            stage={selectedStageData.stage}
            run={selectedStageData.run}
            status={selectedStageData.status}
            onNavigateLineage={(nodeId) => {
              setSelectedStageData(null);
              navigate(`/lineage?node=${nodeId}`);
            }}
          />
        )}
      </SidePanel>
    </div>
  );
};

// -------------------------------------------------------------
// Component: JobWorkflowLane (Horizontally scrollable lane)
// -------------------------------------------------------------
interface JobWorkflowLaneProps {
  job: { id: string; name: string; target: string; category: string };
  runsByJobAndStage: Map<string, PipelineRunItem>;
  onStageClick: (
    jobId: string, 
    jobName: string, 
    stage: string, 
    run?: PipelineRunItem, 
    status?: 'SUCCESS' | 'WARNING' | 'FAILED' | 'SKIPPED'
  ) => void;
}

const JobWorkflowLane: React.FC<JobWorkflowLaneProps> = ({
  job,
  runsByJobAndStage,
  onStageClick,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Compute lane status
  let hasFailed = false;
  let hasWarning = false;
  let totalLaneDuration = 0;

  const stageStatuses = STAGE_ORDER.map((stage) => {
    const run = runsByJobAndStage.get(`${job.id}:${stage}`);
    let computedStatus: 'SUCCESS' | 'WARNING' | 'FAILED' | 'SKIPPED' = 'SUCCESS';

    if (hasFailed) {
      computedStatus = 'SKIPPED';
    } else if (run) {
      totalLaneDuration += run.duration_sec || 0;
      if (run.status === 'FAILED') {
        computedStatus = 'FAILED';
        hasFailed = true;
      } else if (run.status === 'WARNING' || (run.z_score && run.z_score > 2.0) || run.duration_sec > (run.baseline_duration_sec || 20) * 1.5) {
        computedStatus = 'WARNING';
        hasWarning = true;
      } else {
        computedStatus = 'SUCCESS';
      }
    } else {
      computedStatus = hasFailed ? 'SKIPPED' : 'SUCCESS';
    }

    return { stage, run, computedStatus };
  });

  const laneOverallStatus = hasFailed ? 'FAILED' : hasWarning ? 'LATE' : 'HEALTHY';

  // Drag-to-scroll implementation
  const isDragging = useRef(false);
  const startX = useRef(0);
  const scrollLeftStart = useRef(0);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!scrollContainerRef.current) return;
    isDragging.current = true;
    startX.current = e.pageX - scrollContainerRef.current.offsetLeft;
    scrollLeftStart.current = scrollContainerRef.current.scrollLeft;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current || !scrollContainerRef.current) return;
    e.preventDefault();
    const x = e.pageX - scrollContainerRef.current.offsetLeft;
    const walk = (x - startX.current) * 1.5;
    scrollContainerRef.current.scrollLeft = scrollLeftStart.current - walk;
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  const scrollBy = (offset: number) => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: offset, behavior: 'smooth' });
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-card p-4 sm:p-5 space-y-4">
      {/* Lane Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-slate-50 border border-slate-200/80 text-slate-700">
            <Database className="w-4 h-4 text-brand-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900">{job.name}</h3>
              <span className="text-[11px] font-mono text-slate-500">({job.id})</span>
              <span
                className={`px-2 py-0.5 text-[10px] font-bold rounded-md uppercase tracking-wider ${
                  laneOverallStatus === 'FAILED'
                    ? 'bg-rose-100 text-rose-800'
                    : laneOverallStatus === 'LATE'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-emerald-100 text-emerald-800'
                }`}
              >
                {laneOverallStatus}
              </span>
            </div>
            <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2">
              <span>Target: <strong className="text-slate-600">{job.target}</strong></span>
              <span>•</span>
              <span>Total Duration: <strong className="text-slate-600">{totalLaneDuration.toFixed(1)}s</strong></span>
            </div>
          </div>
        </div>

        {/* Scroll Arrow Buttons */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => scrollBy(-260)}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            title="Scroll Left"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => scrollBy(260)}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            title="Scroll Right"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Lane Workflow Strip (Horizontally Scrollable) */}
      <div
        ref={scrollContainerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') scrollBy(120);
          if (e.key === 'ArrowLeft') scrollBy(-120);
        }}
        className="flex items-center gap-2 overflow-x-auto pb-3 pt-1 scroll-smooth cursor-grab active:cursor-grabbing focus:outline-none focus:ring-1 focus:ring-brand-400/50 rounded-xl"
        style={{ scrollSnapType: 'x mandatory' }}
      >
        {stageStatuses.map((item, idx) => {
          const isLast = idx === stageStatuses.length - 1;
          const { stage, run, computedStatus } = item;

          return (
            <React.Fragment key={stage}>
              <StageCard
                stage={stage}
                jobName={job.name}
                run={run}
                status={computedStatus}
                onClick={() => onStageClick(job.id, job.name, stage, run, computedStatus)}
              />
              {!isLast && (
                <div className="flex-shrink-0 text-slate-300">
                  <ChevronRight className="w-5 h-5 stroke-[2.5]" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// Component: StageCard
// -------------------------------------------------------------
interface StageCardProps {
  stage: string;
  jobName: string;
  run?: PipelineRunItem;
  status: 'SUCCESS' | 'WARNING' | 'FAILED' | 'SKIPPED';
  onClick: () => void;
}

const StageCard: React.FC<StageCardProps> = ({
  stage,
  jobName,
  run,
  status,
  onClick,
}) => {
  const duration = run?.duration_sec ?? 18.0;
  const baseline = run?.baseline_duration_sec ?? 20.0;
  const rowsLoaded = run?.rows_loaded ?? 0;
  const startTime = run?.start_time ? run.start_time.substring(11, 19) : '01:00:00';

  // Percentage comparison vs baseline
  const pctOfBaseline = Math.min(200, Math.round((duration / Math.max(baseline, 1)) * 100));

  let cardBg = 'bg-white border-slate-200/90 hover:border-brand-400';
  let badgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  let barColor = 'bg-emerald-500';
  let icon = <CheckCircle2 className="w-4 h-4 text-emerald-600" />;

  if (status === 'SKIPPED') {
    cardBg = 'bg-slate-50/70 border-slate-200/60 opacity-60 hover:opacity-100';
    badgeColor = 'bg-slate-100 text-slate-500 border-slate-200';
    barColor = 'bg-slate-300';
    icon = <MinusCircle className="w-4 h-4 text-slate-400" />;
  } else if (status === 'FAILED') {
    cardBg = 'bg-rose-50/40 border-rose-300 shadow-xs hover:border-rose-500';
    badgeColor = 'bg-rose-100 text-rose-800 border-rose-200';
    barColor = 'bg-rose-500';
    icon = <XCircle className="w-4 h-4 text-rose-600" />;
  } else if (status === 'WARNING') {
    cardBg = 'bg-amber-50/40 border-amber-300 shadow-xs hover:border-amber-500';
    badgeColor = 'bg-amber-100 text-amber-800 border-amber-200';
    barColor = 'bg-amber-500';
    icon = <AlertTriangle className="w-4 h-4 text-amber-600" />;
  }

  return (
    <div
      onClick={onClick}
      className={`flex-shrink-0 w-[220px] rounded-xl border p-3.5 transition-all cursor-pointer select-none shadow-xs hover:shadow-card hover:-translate-y-0.5 ${cardBg}`}
      style={{ scrollSnapAlign: 'start' }}
    >
      {/* Top Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
          {stage}
        </span>
        <div className="flex items-center gap-1">
          {icon}
          <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded border ${badgeColor}`}>
            {status}
          </span>
        </div>
      </div>

      {/* Duration vs Baseline */}
      <div className="space-y-1 mb-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-900">{duration.toFixed(1)}s</span>
          <span className="text-[11px] text-slate-400">vs {baseline.toFixed(1)}s baseline</span>
        </div>

        {/* Mini Duration Progress Bar */}
        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${barColor}`}
            style={{ width: `${Math.min(100, (pctOfBaseline / 150) * 100)}%` }}
          />
        </div>
      </div>

      {/* Rows & Start Time */}
      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100/80">
        <span>{rowsLoaded.toLocaleString()} rows</span>
        <span className="font-mono text-[10px]">{startTime}</span>
      </div>

      {/* Error Snippet if Failed */}
      {status === 'FAILED' && run?.error_message && (
        <div className="mt-2 text-[10px] font-mono text-rose-700 bg-rose-100/80 p-1.5 rounded border border-rose-200 line-clamp-2">
          {run.error_message}
        </div>
      )}

      {/* SLA Breach Snippet if Slow */}
      {status === 'WARNING' && (
        <div className="mt-2 text-[10px] font-semibold text-amber-800 bg-amber-100/80 px-1.5 py-0.5 rounded border border-amber-200 flex items-center justify-between">
          <span>SLA Breach</span>
          <span>{run?.z_score ? `+${run.z_score}σ` : '+2.5σ'}</span>
        </div>
      )}
    </div>
  );
};

// -------------------------------------------------------------
// Component: StageDetailPanelContent (SidePanel Body)
// -------------------------------------------------------------
interface StageDetailPanelContentProps {
  jobId: string;
  jobName: string;
  stage: string;
  run?: PipelineRunItem;
  status: 'SUCCESS' | 'WARNING' | 'FAILED' | 'SKIPPED';
  onNavigateLineage: (nodeId: string) => void;
}

const StageDetailPanelContent: React.FC<StageDetailPanelContentProps> = ({
  jobId,
  jobName,
  stage,
  run,
  status,
  onNavigateLineage,
}) => {
  const duration = run?.duration_sec ?? 18.0;
  const baseline = run?.baseline_duration_sec ?? 20.0;
  const zScore = run?.z_score ?? 0.0;
  const rowsLoaded = run?.rows_loaded ?? 0;
  const jobNodeId = run?.node_id || `job_${jobId}`;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* 1. Header Overview Card */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Execution Status
          </span>
          <span
            className={`px-2.5 py-1 text-xs font-bold rounded-lg border uppercase ${
              status === 'FAILED'
                ? 'bg-rose-100 text-rose-800 border-rose-300'
                : status === 'WARNING'
                ? 'bg-amber-100 text-amber-800 border-amber-300'
                : status === 'SKIPPED'
                ? 'bg-slate-100 text-slate-600 border-slate-300'
                : 'bg-emerald-100 text-emerald-800 border-emerald-300'
            }`}
          >
            {status}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="text-slate-400 block mb-0.5">Job ID</span>
            <span className="font-semibold text-slate-800">{jobId}</span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">Stage</span>
            <span className="font-semibold text-slate-800 uppercase">{stage}</span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">Start Time</span>
            <span className="font-mono text-slate-700">{run?.start_time || 'N/A'}</span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">End Time</span>
            <span className="font-mono text-slate-700">{run?.end_time || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* 2. Statistical Baseline Comparison */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 uppercase tracking-wide">
            <TrendingUp className="w-4 h-4 text-brand-600" />
            <span>Statistical SLA Comparison</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-600">
            Z-Score: {zScore > 0 ? `+${zScore.toFixed(2)}` : zScore.toFixed(2)}σ
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
          <div className="p-3 bg-slate-50 rounded-lg">
            <span className="text-[11px] text-slate-400 block mb-1">Observed Runtime</span>
            <span className="text-xl font-bold text-slate-900">{duration.toFixed(1)}s</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg">
            <span className="text-[11px] text-slate-400 block mb-1">14-Day Baseline SLA</span>
            <span className="text-xl font-bold text-slate-900">{baseline.toFixed(1)}s</span>
          </div>
        </div>

        <div className="pt-2">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Deviation vs Baseline</span>
            <span>{((duration / Math.max(baseline, 1)) * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full ${
                status === 'FAILED'
                  ? 'bg-rose-500'
                  : status === 'WARNING'
                  ? 'bg-amber-500'
                  : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, (duration / (baseline * 1.5)) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* 3. Volume Metrics */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">
            Data Volume Processed
          </span>
          <span className="text-sm font-bold text-slate-900">
            {rowsLoaded.toLocaleString()} rows
          </span>
        </div>
      </div>

      {/* 4. Error Details (if Failed) */}
      {status === 'FAILED' && run?.error_message && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-rose-900 uppercase tracking-wide">
            <AlertOctagon className="w-4 h-4 text-rose-600" />
            <span>Failure Exception Trace</span>
          </div>
          <p className="text-xs font-mono text-rose-800 bg-white/80 p-2.5 rounded-lg border border-rose-200/60 whitespace-pre-wrap">
            {run.error_message}
          </p>
        </div>
      )}

      {/* 5. Related Alert (if present) */}
      {run?.related_alert && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900 uppercase tracking-wide">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Correlated Active Alert</span>
          </div>
          <p className="text-xs text-amber-800 font-medium">
            {run.related_alert}
          </p>
        </div>
      )}

      {/* 6. Action Link to Lineage */}
      <div className="pt-2">
        <button
          onClick={() => onNavigateLineage(jobNodeId)}
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs rounded-xl shadow-sm transition-all"
        >
          <span>View Job in Lineage & Blast Radius</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};