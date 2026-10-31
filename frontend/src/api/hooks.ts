/**
 * TanStack Query Hooks for OpsLens API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from './client';
import type {
  LineageGraphResponse,
  HealthResponse,
  TrustScoreItem,
  TrustHistoryItem,
  AlertItem,
  FaultStatusResponse,
  FaultInjectionResponse,
  TimelineEventItem,
  TimelineSummary,
  PipelineRunItem,
  DaySummaryItem,
} from '../types/api';

export const QUERY_KEYS = {
  lineage: ['lineage'],
  health: ['health'],
  trust: ['trust'],
  trustHistory: (name?: string) => ['trustHistory', name],
  alerts: (status?: string) => ['alerts', status],
  faultStatus: ['faultStatus'],
  runs: (filters?: Record<string, any>) => ['runs', filters],
  runsCalendar: ['runsCalendar'],
  timeline: ['timeline'],
  timelineSummary: ['timelineSummary'],
};

// 1. Lineage Graph (refetches every 5 seconds on lineage page)
export function useLineageGraph(refetchInterval: number | false = 5000) {
  return useQuery<LineageGraphResponse>({
    queryKey: QUERY_KEYS.lineage,
    queryFn: () => fetchApi<LineageGraphResponse>('/api/lineage'),
    refetchInterval,
  });
}

// 2. Health & Live Status
export function useHealth(refetchInterval: number | false = 8000) {
  return useQuery<HealthResponse>({
    queryKey: QUERY_KEYS.health,
    queryFn: () => fetchApi<HealthResponse>('/api/health'),
    refetchInterval,
  });
}

// 3. Trust Scores
export function useTrustScores() {
  return useQuery<TrustScoreItem[]>({
    queryKey: QUERY_KEYS.trust,
    queryFn: () => fetchApi<TrustScoreItem[]>('/api/trust'),
  });
}

// 4. Trust History (for sidepanel sparkline)
export function useTrustHistory(objectName?: string, days = 7) {
  return useQuery<TrustHistoryItem[]>({
    queryKey: QUERY_KEYS.trustHistory(objectName),
    queryFn: () => {
      const q = objectName ? `?object_name=${encodeURIComponent(objectName)}&days=${days}` : `?days=${days}`;
      return fetchApi<TrustHistoryItem[]>(`/api/trust/history${q}`);
    },
    enabled: !!objectName,
  });
}

// 5. Active Alerts
export function useAlerts(status = 'OPEN') {
  return useQuery<AlertItem[]>({
    queryKey: QUERY_KEYS.alerts(status),
    queryFn: () => fetchApi<AlertItem[]>(`/api/alerts?status=${status}`),
  });
}

// 6. Fault Status
export function useFaultStatus(refetchInterval: number | false = 5000) {
  return useQuery<FaultStatusResponse>({
    queryKey: QUERY_KEYS.faultStatus,
    queryFn: () => fetchApi<FaultStatusResponse>('/api/faults/status'),
    refetchInterval,
  });
}

// 7. Timeline Events (polling every 5 seconds)
export function useTimelineEvents(refetchInterval: number | false = 5000) {
  return useQuery<TimelineEventItem[]>({
    queryKey: QUERY_KEYS.timeline,
    queryFn: () => fetchApi<TimelineEventItem[]>('/api/timeline'),
    refetchInterval,
  });
}

// 8. Timeline Summary Metrics (MTTD, MTTR, Open Alerts)
export function useTimelineSummary(refetchInterval: number | false = 5000) {
  return useQuery<TimelineSummary>({
    queryKey: QUERY_KEYS.timelineSummary,
    queryFn: () => fetchApi<TimelineSummary>('/api/timeline/summary'),
    refetchInterval,
  });
}

// 9. Pipeline Runs Telemetry
export function usePipelineRuns(
  filters?: { days?: number; jobId?: string; date?: string },
  refetchInterval: number | false = 5000
) {
  return useQuery<PipelineRunItem[]>({
    queryKey: QUERY_KEYS.runs(filters),
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.days) params.set('days', filters.days.toString());
      if (filters?.jobId) params.set('job_id', filters.jobId);
      if (filters?.date) params.set('date', filters.date);
      const queryStr = params.toString() ? `?${params.toString()}` : '';
      return fetchApi<PipelineRunItem[]>(`/api/runs${queryStr}`);
    },
    refetchInterval,
  });
}

// 10. Runs 14-day Calendar
export function useRunsCalendar(days = 14, refetchInterval: number | false = 10000) {
  return useQuery<DaySummaryItem[]>({
    queryKey: QUERY_KEYS.runsCalendar,
    queryFn: () => fetchApi<DaySummaryItem[]>(`/api/runs/calendar?days=${days}`),
    refetchInterval,
  });
}

// 11. Inject Fault Mutation
export function useInjectFaultMutation() {
  const queryClient = useQueryClient();
  return useMutation<FaultInjectionResponse, Error, string>({
    mutationFn: (faultName: string) =>
      fetchApi<FaultInjectionResponse>(`/api/faults/${faultName}`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.lineage });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.health });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.trust });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.faultStatus });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.timeline });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.timelineSummary });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.runsCalendar });
    },
  });
}

// 12. Reset Mutation
export function useResetFaultsMutation() {
  const queryClient = useQueryClient();
  return useMutation<{ status: string; message?: string }, Error, void>({
    mutationFn: () =>
      fetchApi<{ status: string; message?: string }>('/api/faults/reset', {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.lineage });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.health });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.trust });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.faultStatus });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.timeline });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.timelineSummary });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.runsCalendar });
    },
  });
}

// 13. Run Checks Mutation
export function useRunChecksMutation() {
  const queryClient = useQueryClient();
  return useMutation<any, Error, void>({
    mutationFn: () =>
      fetchApi<any>('/api/checks/run', {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.lineage });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.health });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.trust });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.timeline });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.timelineSummary });
    },
  });
}
