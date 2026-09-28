import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';

interface RawScenario {
  scenario_id: string;
  name_zh: string;
  name_en: string;
  cells: Array<{ cell_id: string; position: number[]; tx_power_dbm: number }>;
  ues: Array<{ ue_id: string }>;
  candidate_k: number;
  metadata?: Record<string, unknown>;
}

export interface MultiCellScenarioSummary {
  scenario_id: string;
  name_zh: string;
  name_en: string;
  cells: RawScenario['cells'];
  ue_count: number;
  candidate_k: number;
  channel: { model: string; frozen: boolean; channel_hash?: string };
  simulation_only: boolean;
}

export interface AssociationOptimizationResponse {
  optimization_id: string;
  scenario_id: string;
  status: string;
  baseline: { network_throughput_mbps: number; p5_throughput_mbps: number };
  best: { network_throughput_mbps: number; p5_throughput_mbps: number; feasible: boolean };
  evaluation_budget: { evaluations_used: number; max_evaluations: number };
  evidence?: { evidence_id: string; acceptance_eligible: boolean; measured: boolean; huawei: boolean };
}

export const userAssociationKeys = {
  scenarios: ['multicell-scenarios'] as const,
  scenario: (id: string) => ['multicell-scenario', id] as const,
};

export async function fetchMultiCellScenarios(): Promise<MultiCellScenarioSummary[]> {
  const { data } = await apiClient.get<{ items: RawScenario[] }>('/multicell/scenarios');
  return data.items.map((raw) => toSummary(raw));
}

export async function fetchMultiCellScenario(id: string): Promise<MultiCellScenarioSummary> {
  const { data } = await apiClient.get<{ scenario: RawScenario; channel?: MultiCellScenarioSummary['channel'] }>(`/multicell/scenarios/${encodeURIComponent(id)}`);
  return toSummary(data.scenario, data.channel);
}

function toSummary(raw: RawScenario, channel?: MultiCellScenarioSummary['channel']): MultiCellScenarioSummary {
  return {
    scenario_id: raw.scenario_id,
    name_zh: raw.name_zh,
    name_en: raw.name_en,
    cells: raw.cells,
    ue_count: raw.ues.length,
    candidate_k: raw.candidate_k,
    channel: channel ?? { model: 'Sionna RT frozen channel', frozen: true },
    simulation_only: true,
  };
}

export async function createUserAssociationOptimization(body: { scenario_id: string; evaluation_budget: number }) {
  const { data } = await apiClient.post<AssociationOptimizationResponse>('/user-association-optimizations', body);
  return data;
}

export function useMultiCellScenarios() {
  return useQuery({ queryKey: userAssociationKeys.scenarios, queryFn: fetchMultiCellScenarios });
}

export function useMultiCellScenario(id: string) {
  return useQuery({ queryKey: userAssociationKeys.scenario(id), queryFn: () => fetchMultiCellScenario(id), enabled: Boolean(id) });
}

export function useCreateUserAssociationOptimization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createUserAssociationOptimization,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userAssociationKeys.scenarios }),
  });
}
