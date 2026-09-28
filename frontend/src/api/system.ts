import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ListResponse } from '../types/common';
import type {
  KpiDefinition,
  SystemBackendView,
  SystemExperimentCreateRequest,
  SystemExperimentList,
  SystemExperimentResponse,
  SystemScenarioDetail,
  SystemScenarioSummary,
} from '../types/system';
import { apiClient } from './client';

export const systemKeys = {
  all: ['system'] as const,
  backends: ['system', 'backends'] as const,
  scenarios: ['system', 'scenarios'] as const,
  scenario: (id: string) => ['system', 'scenarios', id] as const,
  kpis: ['system', 'kpis'] as const,
  experiments: ['system', 'experiments'] as const,
  list: (limit: number, offset: number) => ['system', 'experiments', 'list', limit, offset] as const,
  detail: (id: string) => ['system', 'experiments', 'detail', id] as const,
};

export async function fetchSystemBackends(): Promise<SystemBackendView[]> {
  const { data } = await apiClient.get<ListResponse<SystemBackendView>>('/system-backends');
  return data.items;
}

export async function fetchSystemScenarios(): Promise<SystemScenarioSummary[]> {
  const { data } = await apiClient.get<ListResponse<SystemScenarioSummary>>('/system-scenarios');
  return data.items;
}

export async function fetchSystemScenario(id: string): Promise<SystemScenarioDetail> {
  const { data } = await apiClient.get<SystemScenarioDetail>(`/system-scenarios/${encodeURIComponent(id)}`);
  return data;
}

export async function fetchKpiDefinitions(): Promise<KpiDefinition[]> {
  const { data } = await apiClient.get<ListResponse<KpiDefinition>>('/kpis');
  return data.items;
}

export async function fetchSystemExperiments(limit: number, offset: number): Promise<SystemExperimentList> {
  const { data } = await apiClient.get<SystemExperimentList>('/system-experiments', { params: { limit, offset } });
  return data;
}

export async function fetchSystemExperiment(id: string): Promise<SystemExperimentResponse> {
  const { data } = await apiClient.get<SystemExperimentResponse>(`/system-experiments/${encodeURIComponent(id)}`);
  return data;
}

/** POST /system-experiments：HTTP 201 不代表成功，必须检查返回体 status（可能为 failed）。 */
export async function createSystemExperiment(body: SystemExperimentCreateRequest): Promise<SystemExperimentResponse> {
  const { data } = await apiClient.post<SystemExperimentResponse>('/system-experiments', body);
  return data;
}

export function useSystemBackends() {
  return useQuery({ queryKey: systemKeys.backends, queryFn: fetchSystemBackends, staleTime: 60_000 });
}

export function useSystemScenarios() {
  return useQuery({ queryKey: systemKeys.scenarios, queryFn: fetchSystemScenarios, staleTime: 60_000 });
}

export function useSystemScenario(id: string | null) {
  return useQuery({
    queryKey: systemKeys.scenario(id ?? ''),
    queryFn: () => fetchSystemScenario(id ?? ''),
    enabled: id !== null,
    staleTime: 60_000,
  });
}

export function useKpiDefinitions() {
  return useQuery({ queryKey: systemKeys.kpis, queryFn: fetchKpiDefinitions, staleTime: 5 * 60_000 });
}

export function useSystemExperiments(limit: number, offset: number) {
  return useQuery({
    queryKey: systemKeys.list(limit, offset),
    queryFn: () => fetchSystemExperiments(limit, offset),
    placeholderData: keepPreviousData,
  });
}

export function useSystemExperiment(id: string) {
  return useQuery({
    queryKey: systemKeys.detail(id),
    queryFn: () => fetchSystemExperiment(id),
    refetchInterval: (query) =>
      query.state.data && (query.state.data.status === 'created' || query.state.data.status === 'running')
        ? 2000
        : false,
  });
}

export function useCreateSystemExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createSystemExperiment,
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: systemKeys.experiments });
    },
  });
}
