import { useQuery } from '@tanstack/react-query';

import type { ListResponse } from '../types/common';
import type { ScenarioDetail, ScenarioSummary } from '../types/scenario';
import { apiClient } from './client';

export const scenarioKeys = {
  all: ['scenarios'] as const,
  detail: (id: string) => ['scenarios', id] as const,
};

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const { data } = await apiClient.get<ListResponse<ScenarioSummary>>('/scenarios');
  return data.items;
}

export async function fetchScenario(id: string): Promise<ScenarioDetail> {
  const { data } = await apiClient.get<ScenarioDetail>(`/scenarios/${encodeURIComponent(id)}`);
  return data;
}

export function useScenarios() {
  return useQuery({ queryKey: scenarioKeys.all, queryFn: fetchScenarios });
}

export function useScenario(id: string, enabled = true) {
  return useQuery({
    queryKey: scenarioKeys.detail(id),
    queryFn: () => fetchScenario(id),
    enabled: enabled && id.length > 0,
  });
}
