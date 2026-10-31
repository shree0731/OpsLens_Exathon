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
} from '../types/api';

export const QUERY_KEYS = {
  lineage: ['lineage'],
  health: ['health'],
  trust: ['trust'],
  trustHistory: (name?: string) => ['trustHistory', name],
  alerts: (status?: string) => ['alerts', status],
  faultStatus: ['faultStatus'],
  runs: ['runs'],
  timeline: ['timeline'],
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

// 7. Inject Fault Mutation
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
    },
  });
}

// 8. Reset Mutation
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
    },
  });
}

// 9. Run Checks Mutation
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
    },
  });
}
