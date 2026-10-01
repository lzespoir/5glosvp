import { apiClient } from './client';

export type Source = 'USER_DEFINED' | 'EXPERT_DEFINED' | 'IMPORTED' | 'TEMPLATE_DERIVED' | 'CLONED_VARIANT' | 'CANDIDATE_PROMOTED' | 'GENERATED' | 'MEASURED' | 'MODEL_DEFAULT' | 'BACKEND_DEFAULT' | 'UNKNOWN';
export interface Coordinate { coordinate_system: string; unit: string; origin: string; source: Source; status: 'CONFIRMED' | 'DECLARED' | 'UNKNOWN' }
export interface Position { x: number; y: number; z: number; coordinate: Coordinate }
export interface Parameter { value: number | string | null; unit: string; source: Source; source_version?: string | null }
export interface Site { site_id: string; name: string; position: Position; source: Source; version: number }
export interface Cell { cell_id: string; site_id: string; name: string; position: Position | null; core: Record<string, Parameter>; antenna: { antenna_definition_id: string | null; aau_definition_id: string | null; source: Source }; network_parameters: Record<string, Parameter>; resource_parameters: Record<string, Parameter>; backend_extensions: Record<string, object>; source: Source; version: number }
export interface Antenna { antenna_definition_id: string; name: string; provider_type: string; provider_status: string; source: Source; beam_count: number | null; coordinate: Coordinate; normalization: string; calibration_status: string; supported_backends: string[]; artifact_id: string | null; artifact_hash: string | null; profile_id: string | null; parameters: Record<string, unknown>; version: number }
export interface UE { ue_id: string; position: Position | null; mobility: string; traffic_profile: string; serving_cell_id: string | null; source: Source }
export interface EnvironmentAsset { asset_id: string; name: string; asset_type: string; source_path: string | null; size_bytes: number | null; sha256: string | null; coordinate: Coordinate; metadata: Record<string, unknown>; supported_backends: string[]; conversion_status: string; source: Source; version: number }
export interface Scenario {
  scenario_id: string; name: string; family: string; classification: Record<string, string>; environment: { environment_id: string; asset_id: string | null; asset_sha256: string | null; coordinate: Coordinate; layers: { layer_id: string; kind: string; visible: boolean; source_asset_id?: string | null; status: string }[]; supported_backends: string[]; version: number } | null;
  sites: Site[]; cells: Cell[]; antennas: Antenna[]; ues: UE[];
  traffic: { kind: string; availability: string; source: Source }; radio: { backend: string; status: string; version: string; calibration_status: string };
  network_functions: string[]; optimization_problems: string[]; candidate_hash: string | null; source: Source; state: string; version: number; definition_hash: string; created_at: string; updated_at: string; lineage: Record<string, unknown>;
  pre_archive_state: string | null; archived_at: string | null; archived_source: string | null; restored_at: string | null; restored_source: string | null;
}
export interface Validation { issues: { severity: string; code: string; path: string; message: string }[]; config_valid: boolean; simulation_ready: boolean; experiment_ready: boolean; state: string }
export interface Counts { configured_scenario_count: number; runnable_scenario_count: number; executed_scenario_count: number; experiment_verified_count: number; acceptance_evidence_count: number }
export interface WorkspaceCoverage { source: 'PERSISTED_CONFIGURED_SCENARIOS'; configured_scenario_count: number; family_counts: Record<string, number>; problem_counts: Record<string, number>; matrix: { family: string; problem_type: string; configured_count: number }[] }
export interface Capability { capability_id: string; name: string; status: string; implementation_version: string | null; evidence_refs: string[]; limitations: string[]; last_verified_at: string | null }

export const workspaceApi = {
  counts: async () => (await apiClient.get<Counts>('/workspace/counts')).data,
  coverage: async () => (await apiClient.get<WorkspaceCoverage>('/workspace/coverage')).data,
  capabilities: async () => (await apiClient.get<{ items: Capability[] }>('/workspace/capabilities')).data.items,
  list: async (params: Record<string, string | number>) => (await apiClient.get<{ items: Scenario[]; total: number }>('/workspace/scenarios', { params })).data,
  get: async (id: string) => (await apiClient.get<Scenario>(`/workspace/scenarios/${id}`)).data,
  validation: async (id: string) => (await apiClient.get<Validation>(`/workspace/scenarios/${id}/validation`)).data,
  create: async (name: string, family: string) => (await apiClient.post<Scenario>('/workspace/scenarios', { name, family })).data,
  clone: async (id: string) => (await apiClient.post<Scenario>(`/workspace/scenarios/${id}/clone`)).data,
  archive: async (id: string) => (await apiClient.post<Scenario>(`/workspace/scenarios/${id}/archive`)).data,
  restore: async (id: string) => (await apiClient.post<Scenario>(`/workspace/scenarios/${id}/restore`)).data,
  deleteScenario: async (id: string) => (await apiClient.delete<{ scenario_id: string; deleted: boolean; cascade_deleted: false }>(`/workspace/scenarios/${id}`)).data,
  patch: async (id: string, section: string, expected_version: number, value: unknown) => (await apiClient.patch<Scenario>(`/workspace/scenarios/${id}/${section}`, { expected_version, value })).data,
  assets: async () => (await apiClient.get<{ items: EnvironmentAsset[] }>('/workspace/assets')).data.items,
  registerAsset: async (value: { name: string; asset_type: string; source_path: string; coordinate: Coordinate }) => (await apiClient.post<EnvironmentAsset>('/workspace/assets', value)).data,
  materialize: async (id: string, seed: number) => (await apiClient.post<{ instance_id: string; identity_hash: string; run_status: string }>(`/workspace/scenarios/${id}/instances`, { seed })).data,
  batchEditCells: async (id: string, expected_version: number, cell_ids: string[], updates: Record<string, Parameter>) => (await apiClient.post<Scenario>(`/workspace/scenarios/${id}/cells/batch-edit`, { expected_version, cell_ids, updates })).data,
};

export const declaredCoordinate = (name: string, unit: string): Coordinate => ({ coordinate_system: name, unit, origin: 'USER_DECLARED', source: 'USER_DEFINED', status: 'DECLARED' });
export const position = (x: number, y: number, z: number, coordinate: Coordinate): Position => ({ x, y, z, coordinate });
export const parameter = (value: number | null, unit: string): Parameter => ({ value, unit, source: 'USER_DEFINED' });
