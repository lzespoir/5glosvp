import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';

export interface BenchmarkAlgorithm {
  algorithm_id: string;
  name: string;
  version: string;
  category: string;
  provider: string;
  learning_algorithm: boolean;
  runnable: boolean;
  compatibility: { status: string; reason: string; parameter_types: string[]; constraint_types: string[] };
}

export interface ResearchReference { reference_id: string; algorithm_family: string; paper_title: string; implementation_status: string; notes: string; }
export interface BenchmarkSummary {
  benchmark_id: string;
  protocol_id: string;
  protocol_hash: string;
  status: string;
  scenario_set: string[];
  results: Array<Record<string, unknown>>;
  provenance: { data_source: string; verification: string; evidence_level: string; comparison_eligible: boolean; channel_hash: string };
}
export interface BenchmarkDetail {
  benchmark: Record<string, any>;
  protocol: Record<string, any>;
  algorithms: { runnable: BenchmarkAlgorithm[]; research: ResearchReference[] };
  runs: Array<Record<string, any>>;
  comparison: Array<Record<string, any>>;
  convergence: Record<string, Array<Record<string, any>>>;
  verification: Record<string, any>;
  evidence: Record<string, any>;
  provenance: Record<string, any>;
  closure: Record<string, any> | null;
}

export const benchmarkKeys = { all: ['benchmarks'] as const, algorithms: ['benchmark-algorithms'] as const, protocols: ['benchmark-protocols'] as const };
export async function fetchBenchmarkAlgorithms() { const { data } = await apiClient.get<{ runnable: BenchmarkAlgorithm[]; research: ResearchReference[] }>('/benchmarks/algorithms'); return data; }
export async function fetchBenchmarkProtocols() { const { data } = await apiClient.get<{ items: Array<Record<string, unknown>> }>('/benchmarks/protocols'); return data.items; }
export async function fetchBenchmarks() { const { data } = await apiClient.get<{ items: BenchmarkSummary[] }>('/benchmarks'); return data.items; }
export async function createBenchmark(body: { scenario_id: string; evaluation_budget: number }) { const { data } = await apiClient.post<BenchmarkSummary>('/benchmarks', body); return data; }
export async function fetchBenchmarkDetail(benchmarkId: string) { const { data } = await apiClient.get<BenchmarkDetail>(`/benchmarks/${benchmarkId}/detail`); return data; }
export function useBenchmarkAlgorithms() { return useQuery({ queryKey: benchmarkKeys.algorithms, queryFn: fetchBenchmarkAlgorithms }); }
export function useBenchmarkProtocols() { return useQuery({ queryKey: benchmarkKeys.protocols, queryFn: fetchBenchmarkProtocols }); }
export function useBenchmarks() { return useQuery({ queryKey: benchmarkKeys.all, queryFn: fetchBenchmarks }); }
export function useCreateBenchmark() { const client = useQueryClient(); return useMutation({ mutationFn: createBenchmark, onSuccess: () => client.invalidateQueries({ queryKey: benchmarkKeys.all }) }); }
export function useBenchmarkDetail(benchmarkId: string) { return useQuery({ queryKey: [...benchmarkKeys.all, benchmarkId], queryFn: () => fetchBenchmarkDetail(benchmarkId), enabled: Boolean(benchmarkId) }); }
