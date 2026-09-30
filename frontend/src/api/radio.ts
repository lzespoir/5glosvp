import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';

export interface RadioScenarioSummary {
  scenario_id: string;
  name_zh: string;
  name_en: string;
  scenario_instance_id: string;
  cell_count: number;
  ue_count: number;
  status: string;
}

export interface RadioMetric {
  metric_name: string;
  value: number | null;
  unit: string;
  semantic_type: string;
  source_type: string;
  calibration_status: string;
  notes?: string;
}

export interface RadioCellObservation {
  cell: { cell_id: string; site_id: string; aau_id: string };
  role: 'SERVING' | 'NEIGHBOR' | 'OTHER';
  geometry: { distance_3d_m: number; azimuth_deg: number; elevation_deg: number };
  strongest_relative_beam_id: number | null;
  strongest_relative_response: RadioMetric;
  received_power: { total: RadioMetric; components: RadioMetric[] };
  interference: { aggregate_interference: RadioMetric; noise_floor: RadioMetric; sinr: RadioMetric } | null;
}

export interface RadioObservation {
  observation_set_id: string;
  scenario_id: string;
  scenario_instance_id: string;
  ue: { ue_id: string; position: { x: number; y: number; z: number }; mobility_state: string; traffic_profile: string };
  cells: RadioCellObservation[];
  serving_neighbor: { serving_cell_id: string; serving_selection_source: string; neighbor_cell_ids: string[]; ranked_neighbors: Array<{ cell_id: string; sim_received_power_dbm: number }> };
  identity: { identity_hash: string; radio_context_id: string; a_matrix_artifact_hashes: string[]; lookup_method: string; propagation_backend: string; calibration_status: string };
  calibration_status: string;
  absolute_radio_kpi_status: string;
  provenance: { day13_ue_twin_reused: boolean; a_matrix_raw_npy_modified: boolean; sionna_executed: boolean; measurement_data: boolean };
}

export const radioKeys = {
  scenarios: ['day14', 'radio', 'scenarios'] as const,
  observation: (scenarioId: string, ueId: string) => ['day14', 'radio', scenarioId, ueId] as const,
};

async function fetchScenarios(): Promise<RadioScenarioSummary[]> {
  const { data } = await apiClient.get<{ items: RadioScenarioSummary[] }>('/radio/scenarios');
  return data.items;
}

async function fetchObservation(scenarioId: string, ueId: string): Promise<RadioObservation> {
  const { data } = await apiClient.get<RadioObservation>(`/radio/scenarios/${scenarioId}/ues/${ueId}/observations`);
  return data;
}

export function useRadioScenarios() {
  return useQuery({ queryKey: radioKeys.scenarios, queryFn: fetchScenarios, staleTime: 60_000 });
}

export function useRadioObservation(scenarioId: string, ueId: string) {
  return useQuery({ queryKey: radioKeys.observation(scenarioId, ueId), queryFn: () => fetchObservation(scenarioId, ueId), enabled: Boolean(scenarioId && ueId), staleTime: 60_000 });
}
