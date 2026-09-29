import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';

export interface PackageRecord {
  package_id: string;
  algorithm_id: string;
  algorithm_version: string;
  package_hash: string;
  manifest_hash: string;
  source_hash: string;
  path: string;
  status: string;
  disabled?: boolean;
  manifest: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface PackageCheck {
  status: string;
  stage?: string;
  errors?: Array<Record<string, any>>;
  package_id?: string;
  package_hash?: string;
  manifest_hash?: string;
  source_hash?: string;
  manifest?: Record<string, any>;
  metadata?: Record<string, any>;
  validation?: Record<string, any>;
  real_sionna_used?: boolean;
  lifecycle?: string[];
  evaluations_used?: number;
}

export interface ExternalExperiment {
  run_id: string;
  status: string;
  stage: string;
  package_id: string;
  algorithm_id: string;
  algorithm_version: string;
  package_hash: string;
  scenario_id: string;
  parameters: Record<string, any>;
  evaluation_budget: number;
  time_limit_seconds: number | null;
  evaluations_used?: number;
  stop_reason?: string;
  channel_hash?: string;
  benchmark_id?: string;
  reference_id?: string;
  export_bundle?: string;
  runtime?: Record<string, number>;
  best_candidate?: Record<string, any>;
  baseline?: Record<string, any>;
  logs?: Array<Record<string, any>>;
  trace?: Record<string, any>;
  error?: Record<string, any>;
}

export async function validatePackage(path: string) {
  const { data } = await apiClient.post<PackageCheck>('/algorithm-packages/validate', { path });
  return data;
}

export async function smokeTestPackage(path: string) {
  const { data } = await apiClient.post<PackageCheck>('/algorithm-packages/smoke-test', { path });
  return data;
}

export async function registerPackage(path: string) {
  const { data } = await apiClient.post<PackageRecord | PackageCheck>('/algorithm-packages/register', { path });
  return data;
}

export async function createExternalExperiment(body: {
  package_id: string;
  scenario_id: string;
  parameters: Record<string, any>;
  evaluation_budget: number;
  time_limit_seconds: number | null;
}) {
  const { data } = await apiClient.post<ExternalExperiment>('/algorithm-experiments', body);
  return data;
}

export async function rerunExternalExperiment(runId: string) {
  const { data } = await apiClient.post<ExternalExperiment>(`/algorithm-experiments/${encodeURIComponent(runId)}/rerun`);
  return data;
}

export async function cloneExternalExperiment(runId: string, parameters: Record<string, any>) {
  const { data } = await apiClient.post<ExternalExperiment>(`/algorithm-experiments/${encodeURIComponent(runId)}/clone`, { parameters });
  return data;
}

export function useExternalExperiment(runId: string | null) {
  return useQuery({
    queryKey: ['algorithm-experiments', runId],
    queryFn: async () => (await apiClient.get<ExternalExperiment>(`/algorithm-experiments/${encodeURIComponent(runId as string)}`)).data,
    enabled: !!runId,
    refetchInterval: runId ? 800 : false,
    retry: false,
  });
}
