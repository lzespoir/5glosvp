import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ListResponse } from '../types/common';
import type {
  ObjectiveView,
  OptimizationCreateRequest,
  OptimizationList,
  OptimizationResponse,
  OptimizerView,
} from '../types/optimization';
import { apiClient } from './client';
import { experimentKeys } from './experiments';

export const optimizationKeys = {
  all: ['optimizations'] as const,
  list: (limit: number, offset: number) => ['optimizations', 'list', limit, offset] as const,
  detail: (id: string) => ['optimizations', 'detail', id] as const,
  optimizers: ['optimizers'] as const,
  objectives: ['objectives'] as const,
};

export async function fetchOptimizers(): Promise<OptimizerView[]> {
  const { data } = await apiClient.get<ListResponse<OptimizerView>>('/optimizers');
  return data.items;
}

export async function fetchObjectives(): Promise<ObjectiveView[]> {
  const { data } = await apiClient.get<ListResponse<ObjectiveView>>('/objectives');
  return data.items;
}

export async function fetchOptimizations(limit: number, offset: number): Promise<OptimizationList> {
  const { data } = await apiClient.get<OptimizationList>('/optimizations', { params: { limit, offset } });
  return data;
}

export async function fetchOptimization(id: string): Promise<OptimizationResponse> {
  const { data } = await apiClient.get<OptimizationResponse>(`/optimizations/${encodeURIComponent(id)}`);
  return data;
}

/** POST /optimizations：HTTP 201 不代表成功，必须检查返回体 status（可能为 failed）。 */
export async function createOptimization(body: OptimizationCreateRequest): Promise<OptimizationResponse> {
  const { data } = await apiClient.post<OptimizationResponse>('/optimizations', body);
  return data;
}

export function useOptimizers() {
  return useQuery({ queryKey: optimizationKeys.optimizers, queryFn: fetchOptimizers, staleTime: 60_000 });
}

export function useObjectives() {
  return useQuery({ queryKey: optimizationKeys.objectives, queryFn: fetchObjectives, staleTime: 60_000 });
}

export function useOptimizations(limit: number, offset: number) {
  return useQuery({
    queryKey: optimizationKeys.list(limit, offset),
    queryFn: () => fetchOptimizations(limit, offset),
    placeholderData: keepPreviousData,
  });
}

export function useOptimization(id: string) {
  return useQuery({
    queryKey: optimizationKeys.detail(id),
    queryFn: () => fetchOptimization(id),
    refetchInterval: (query) =>
      query.state.data && (query.state.data.status === 'created' || query.state.data.status === 'running')
        ? 2000
        : false,
  });
}

export function useCreateOptimization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createOptimization,
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: optimizationKeys.all }),
        queryClient.invalidateQueries({ queryKey: experimentKeys.all }),
      ]);
    },
  });
}
