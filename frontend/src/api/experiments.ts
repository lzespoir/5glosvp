import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  ArtifactView,
  ExperimentCreateRequest,
  ExperimentList,
  ExperimentResponse,
} from '../types/experiment';
import type { ListResponse } from '../types/common';
import { isActiveStatus } from '../utils/status';
import { apiClient } from './client';

export const experimentKeys = {
  all: ['experiments'] as const,
  list: (limit: number, offset: number) => ['experiments', 'list', limit, offset] as const,
  detail: (id: string) => ['experiments', 'detail', id] as const,
  artifacts: (id: string) => ['experiments', 'detail', id, 'artifacts'] as const,
};

export async function fetchExperiments(limit: number, offset: number): Promise<ExperimentList> {
  const { data } = await apiClient.get<ExperimentList>('/experiments', { params: { limit, offset } });
  return data;
}

export async function fetchExperiment(id: string): Promise<ExperimentResponse> {
  const { data } = await apiClient.get<ExperimentResponse>(`/experiments/${encodeURIComponent(id)}`);
  return data;
}

export async function fetchArtifacts(id: string): Promise<ArtifactView[]> {
  const { data } = await apiClient.get<ListResponse<ArtifactView>>(
    `/experiments/${encodeURIComponent(id)}/artifacts`,
  );
  return data.items;
}

/**
 * POST /experiments。注意：HTTP 201 只表示实验已创建，
 * 仿真是否成功必须看返回体中的 status（可能为 failed）。
 */
export async function createExperiment(body: ExperimentCreateRequest): Promise<ExperimentResponse> {
  const { data } = await apiClient.post<ExperimentResponse>('/experiments', body);
  return data;
}

export function useExperiments(limit: number, offset: number) {
  return useQuery({
    queryKey: experimentKeys.list(limit, offset),
    queryFn: () => fetchExperiments(limit, offset),
    placeholderData: keepPreviousData,
  });
}

export function useExperiment(id: string, enabled = true) {
  return useQuery({
    queryKey: experimentKeys.detail(id),
    queryFn: () => fetchExperiment(id),
    enabled: enabled && id.length > 0,
    // 未来改为后台执行时，运行中的实验自动轮询
    refetchInterval: (query) =>
      query.state.data && isActiveStatus(query.state.data.status) ? 2000 : false,
  });
}

export function useArtifacts(id: string) {
  return useQuery({ queryKey: experimentKeys.artifacts(id), queryFn: () => fetchArtifacts(id) });
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createExperiment,
    onSettled: () => queryClient.invalidateQueries({ queryKey: experimentKeys.all }),
  });
}
