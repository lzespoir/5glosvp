import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export type ComparisonIntent = 'ALGORITHM_COMPARISON' | 'HYPERPARAMETER_COMPARISON' | 'CONFIGURATION_COMPARISON' | 'RUN_REPRODUCIBILITY' | 'SCENARIO_ANALYSIS' | 'CUSTOM_ANALYSIS';
export interface ComparisonRun { run_id: string; status: string; algorithm_id?: string; algorithm_version?: string; scenario_id?: string; evaluation_budget?: number; created_at?: string; }
export interface ComparisonPreview { preview_id: string; selected_run_ids: string[]; intent: ComparisonIntent; status: string; dimensions: Array<{ name: string; values: unknown[]; equal: boolean; frozen_by_default: boolean; declared_varying: boolean }>; differences: string[]; incompatible_dimensions: string[]; allowed_actions: string[]; message_zh: string; }
export interface ComparisonRecord { comparison_id: string; selected_run_ids: string[]; user_intent: ComparisonIntent; compatibility: ComparisonPreview; verification_status: string; verified: boolean; result_policy: { ranking: boolean; winner: boolean; gain: boolean; a_over_b: boolean }; }

export const comparisonKeys = { all: ['comparisons'] as const, runs: ['comparison-runs'] as const };
export async function fetchComparisonRuns() { const { data } = await apiClient.get<{ items: ComparisonRun[] }>('/comparisons/runs'); return data.items; }
export async function previewComparison(body: { run_ids: string[]; intent: ComparisonIntent; declared_varying_dimensions?: string[] }) { const { data } = await apiClient.post<ComparisonPreview>('/comparisons/preview', body); return data; }
export async function createComparison(body: { run_ids: string[]; intent: ComparisonIntent; declared_varying_dimensions?: string[]; confirmed: boolean }) { const { data } = await apiClient.post<ComparisonRecord>('/comparisons', body); return data; }
export function useComparisonRuns() { return useQuery({ queryKey: comparisonKeys.runs, queryFn: fetchComparisonRuns }); }
export function usePreviewComparison() { return useMutation({ mutationFn: previewComparison }); }
export function useCreateComparison() { const client = useQueryClient(); return useMutation({ mutationFn: createComparison, onSuccess: () => client.invalidateQueries({ queryKey: comparisonKeys.all }) }); }
