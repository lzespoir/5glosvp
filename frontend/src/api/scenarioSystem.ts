import { useMutation, useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { AcceptanceMapping, ScenarioCoverage, ScenarioDefinition, ScenarioPreview, ScenarioTaxonomy, ScenarioWorkspace } from '../types/scenarioSystem';

export const scenarioSystemKeys = {
  taxonomy: ['scenario-system', 'taxonomy'] as const,
  preview: (selection: Record<string, string[]>) => ['scenario-system', 'preview', selection] as const,
  catalog: ['scenario-system', 'catalog'] as const,
  coverage: ['scenario-system', 'coverage'] as const,
  acceptance: ['scenario-system', 'acceptance'] as const,
};

export async function fetchScenarioTaxonomy(): Promise<ScenarioTaxonomy> {
  const { data } = await apiClient.get<ScenarioTaxonomy>('/scenario-system/taxonomy');
  return data;
}

export async function previewScenarioCombination(selection: Record<string, string[]>): Promise<ScenarioPreview> {
  const { data } = await apiClient.post<ScenarioPreview>('/scenario-system/combinations/preview', { selection, limit: 100 });
  return data;
}

export async function fetchScenarioCatalog(): Promise<{ items: ScenarioDefinition[]; total: number }> {
  const { data } = await apiClient.get<{ items: ScenarioDefinition[]; total: number }>('/scenario-system/catalog?limit=120');
  return data;
}

export async function fetchScenarioCoverage(): Promise<ScenarioCoverage> {
  const { data } = await apiClient.get<ScenarioCoverage>('/scenario-system/coverage');
  return data;
}

export async function fetchAcceptanceMapping(): Promise<AcceptanceMapping[]> {
  const { data } = await apiClient.get<{ items: AcceptanceMapping[] }>('/scenario-system/acceptance');
  return data.items;
}

export async function materializeScenario(scenario_id: string): Promise<ScenarioWorkspace> {
  const { data } = await apiClient.post<ScenarioWorkspace>('/scenario-system/materialize', { scenario_id, seed: 0 });
  return data;
}

export function useScenarioTaxonomy() { return useQuery({ queryKey: scenarioSystemKeys.taxonomy, queryFn: fetchScenarioTaxonomy }); }
export function useScenarioPreview(selection: Record<string, string[]>, enabled: boolean) { return useQuery({ queryKey: scenarioSystemKeys.preview(selection), queryFn: () => previewScenarioCombination(selection), enabled, staleTime: 30_000 }); }
export function useScenarioCatalog() { return useQuery({ queryKey: scenarioSystemKeys.catalog, queryFn: fetchScenarioCatalog }); }
export function useScenarioCoverage() { return useQuery({ queryKey: scenarioSystemKeys.coverage, queryFn: fetchScenarioCoverage }); }
export function useAcceptanceMapping() { return useQuery({ queryKey: scenarioSystemKeys.acceptance, queryFn: fetchAcceptanceMapping }); }
export function useMaterializeScenario() { return useMutation({ mutationFn: materializeScenario }); }
