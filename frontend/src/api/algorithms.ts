import { keepPreviousData, useQuery } from '@tanstack/react-query';

import type {
  AlgorithmDetail,
  AlgorithmList,
  AlgorithmValidateRequest,
  CompatibilityReport,
  EvidenceList,
} from '../types/algorithm';
import { apiClient } from './client';

export const algorithmKeys = {
  list: ['algorithms'] as const,
  detail: (id: string) => ['algorithms', 'detail', id] as const,
  validate: (id: string, body: AlgorithmValidateRequest) => ['algorithms', 'validate', id, body] as const,
  evidence: ['evidence'] as const,
};

export async function fetchAlgorithms(): Promise<AlgorithmList> {
  const { data } = await apiClient.get<AlgorithmList>('/algorithms');
  return data;
}

export async function fetchAlgorithm(id: string): Promise<AlgorithmDetail> {
  const { data } = await apiClient.get<AlgorithmDetail>(`/algorithms/${encodeURIComponent(id)}`);
  return data;
}

/** POST /algorithms/{id}/validate：不兼容时 200 + compatible=false；参数空间本身无效时 422。 */
export async function validateAlgorithm(id: string, body: AlgorithmValidateRequest): Promise<CompatibilityReport> {
  const { data } = await apiClient.post<CompatibilityReport>(`/algorithms/${encodeURIComponent(id)}/validate`, body);
  return data;
}

export async function fetchEvidence(): Promise<EvidenceList> {
  const { data } = await apiClient.get<EvidenceList>('/evidence');
  return data;
}

export function useAlgorithms() {
  return useQuery({ queryKey: algorithmKeys.list, queryFn: fetchAlgorithms, staleTime: 60_000 });
}

export function useAlgorithm(id: string) {
  return useQuery({ queryKey: algorithmKeys.detail(id), queryFn: () => fetchAlgorithm(id), enabled: !!id });
}

/** 即时兼容性反馈：请求体变化即重新检查（保留上一次结果避免闪烁）。 */
export function useAlgorithmValidation(id: string | null, body: AlgorithmValidateRequest | null) {
  return useQuery({
    queryKey: id && body ? algorithmKeys.validate(id, body) : ['algorithms', 'validate', 'idle'],
    queryFn: () => validateAlgorithm(id as string, body as AlgorithmValidateRequest),
    enabled: !!id && !!body,
    placeholderData: keepPreviousData,
    retry: false,
    staleTime: 30_000,
  });
}

export function useEvidence() {
  return useQuery({ queryKey: algorithmKeys.evidence, queryFn: fetchEvidence });
}
