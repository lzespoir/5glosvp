import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ListResponse } from '../types/common';
import type {
  BenchmarkProtocol,
  SystemObjectiveView,
  SystemOptimizationCreateRequest,
  SystemOptimizationList,
  SystemOptimizationResponse,
  SystemOptimizerView,
  SystemParameterView,
} from '../types/systemOptimization';
import { apiClient } from './client';
import { systemKeys } from './system';

export const systemOptimizationKeys = {
  all: ['system-optimizations'] as const,
  list: (limit: number, offset: number) => ['system-optimizations', 'list', limit, offset] as const,
  detail: (id: string) => ['system-optimizations', 'detail', id] as const,
  optimizers: ['system-optimizers'] as const,
  objectives: ['system-objectives'] as const,
  parameters: ['system-parameters'] as const,
  protocols: ['benchmark-protocols'] as const,
};

async function fetchItems<T>(path: string): Promise<T[]> {
  const { data } = await apiClient.get<ListResponse<T>>(path);
  return data.items;
}

export async function fetchSystemOptimizations(limit: number, offset: number): Promise<SystemOptimizationList> {
  const { data } = await apiClient.get<SystemOptimizationList>('/system-optimizations', { params: { limit, offset } });
  return data;
}

export async function fetchSystemOptimization(id: string): Promise<SystemOptimizationResponse> {
  const { data } = await apiClient.get<SystemOptimizationResponse>(`/system-optimizations/${encodeURIComponent(id)}`);
  return data;
}

/** POST /system-optimizations：HTTP 202，后台执行；进度通过 GET 轮询 progress 字段获取。 */
export async function createSystemOptimization(body: SystemOptimizationCreateRequest): Promise<SystemOptimizationResponse> {
  const { data } = await apiClient.post<SystemOptimizationResponse>('/system-optimizations', body);
  return data;
}

export function useSystemOptimizers() {
  return useQuery({
    queryKey: systemOptimizationKeys.optimizers,
    queryFn: () => fetchItems<SystemOptimizerView>('/system-optimizers'),
    staleTime: 60_000,
  });
}

export function useSystemObjectives() {
  return useQuery({
    queryKey: systemOptimizationKeys.objectives,
    queryFn: () => fetchItems<SystemObjectiveView>('/system-objectives'),
    staleTime: 60_000,
  });
}

export function useSystemParameters() {
  return useQuery({
    queryKey: systemOptimizationKeys.parameters,
    queryFn: () => fetchItems<SystemParameterView>('/system-parameters'),
    staleTime: 60_000,
  });
}

export function useBenchmarkProtocols() {
  return useQuery({
    queryKey: systemOptimizationKeys.protocols,
    queryFn: () => fetchItems<BenchmarkProtocol>('/benchmark-protocols'),
    staleTime: 60_000,
  });
}

const isActive = (r: SystemOptimizationResponse | undefined) =>
  !!r && (r.status === 'created' || r.status === 'running');

export function useSystemOptimizations(limit: number, offset: number) {
  return useQuery({
    queryKey: systemOptimizationKeys.list(limit, offset),
    queryFn: () => fetchSystemOptimizations(limit, offset),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.items.some(isActive) ? 3000 : false),
  });
}

export function useSystemOptimization(id: string) {
  return useQuery({
    queryKey: systemOptimizationKeys.detail(id),
    queryFn: () => fetchSystemOptimization(id),
    refetchInterval: (query) => (isActive(query.state.data) ? 2000 : false),
  });
}

export function useCreateSystemOptimization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createSystemOptimization,
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: systemOptimizationKeys.all }),
        queryClient.invalidateQueries({ queryKey: systemKeys.experiments }),
      ]);
    },
  });
}
