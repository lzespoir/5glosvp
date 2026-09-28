// 与后端 /api/v1/system-* 与 /api/v1/kpis 契约一致 / Mirrors the system-level API contract.

export type SystemExperimentStatus = 'created' | 'running' | 'succeeded' | 'failed';

/** 结果模型来源：前端据此区分 Sionna 仿真、工程近似与测试夹具。 */
export type SystemModelType = 'sionna_sys' | 'engineering_approximation' | 'test_fixture';

export type KpiScope = 'ue' | 'network';

export interface SystemBackendView {
  id: string;
  name_zh: string;
  name_en: string;
  category: string;
  available: boolean;
  version: string | null;
  capabilities: string[];
  model_type: SystemModelType;
  model_label: string;
  source_type: string;
  provider: string | null;
  compute_device: string | null;
  reason: string | null;
  warnings: string[];
}

export interface AntennaArrayConfig {
  num_rows: number;
  num_cols: number;
  pattern: string;
  polarization: string;
  source: string;
}

export interface BaseStation {
  bs_id: string;
  name: string | null;
  position: number[];
}

export interface Cell {
  cell_id: string;
  bs_id: string;
  position: number[] | null;
  carrier_frequency_hz: number;
  bandwidth_hz: number;
  tx_power_dbm: number;
  antenna: AntennaArrayConfig;
}

export interface UserEquipmentConfig {
  ue_id: string;
  position: number[];
  serving_cell_id: string | null;
}

export interface UeGeneratorConfig {
  type: string;
  count: number;
  seed: number;
  area_center: number[];
  area_size: number[];
  height_m: number;
  max_candidates: number;
  source: string;
}

export interface SystemSimulationConfig {
  num_slots: number;
  subcarrier_spacing_hz: number;
  num_prb: number;
  num_data_symbols_per_slot: number;
  slot_duration_s: number;
  noise_figure_db: number;
  temperature_k: number;
  max_depth: number;
  samples_per_src: number;
  scheduler: { id: string; beta: number };
  link_adaptation: { id: string; bler_target: number; mcs_table_index: number };
  power_control: { id: string; guaranteed_power_ratio: number; fairness: number };
}

export interface SystemScenario {
  scenario_id: string;
  name_zh: string;
  name_en: string;
  description: string | null;
  backend: string;
  scene: string;
  base_stations: BaseStation[];
  cells: Cell[];
  ues: UserEquipmentConfig[];
  ue_generator: UeGeneratorConfig | null;
  traffic: { type: string; direction: string; source: string; tag: string };
  simulation: SystemSimulationConfig;
  seed: number;
  assumptions: string[];
}

export interface SystemScenarioSummary {
  scenario_id: string;
  name_zh: string;
  name_en: string;
  description: string | null;
  backend: string;
  scene: string;
  bs_count: number;
  cell_count: number;
  ue_count: number;
  carrier_frequency_hz: number;
  bandwidth_hz: number;
  traffic_model: string;
  seed: number;
  ue_placement: string;
  data_source: string;
}

export interface SystemScenarioDetail extends SystemScenarioSummary {
  scenario: SystemScenario;
}

export interface UserEquipmentResult {
  ue_id: string;
  serving_cell_id: string;
  position: number[];
  mean_channel_gain_db: number | null;
  sinr_eff_db_mean: number | null;
  mcs_index_mean: number | null;
  scheduled_slots: number;
  acked_slots: number;
  tbler: number | null;
  allocated_re_per_slot_mean: number;
  allocated_re_share: number;
  tx_power_w_mean: number | null;
  decoded_bits: number;
  simulated_duration_s: number;
  throughput_mbps: number | null;
  throughput_metric_id: string | null;
  unavailable: Record<string, string>;
}

export interface SystemRuntime {
  propagation_seconds: number | null;
  system_seconds: number | null;
  total_seconds: number | null;
}

export interface CellTopology {
  cell_id: string;
  bs_id: string;
  position: number[];
  carrier_frequency_hz: number;
  bandwidth_hz: number;
  tx_power_dbm: number;
}

export interface SystemSimulationResult {
  scenario_id: string;
  cells: CellTopology[];
  backend: string;
  backend_version: string | null;
  provider_versions: Record<string, string | null>;
  seed: number;
  num_slots: number;
  slot_duration_s: number;
  simulated_duration_s: number;
  num_data_re_per_slot: number;
  ue_results: UserEquipmentResult[];
  scheduler: Record<string, unknown>;
  link_adaptation: Record<string, unknown>;
  power_control: Record<string, unknown>;
  ue_generation: Record<string, unknown> | null;
  compute_device: string | null;
  runtime: SystemRuntime;
  warnings: string[];
}

export interface KpiResult {
  metric_id: string;
  version: string;
  name_zh: string;
  name_en: string;
  unit: string;
  scope: KpiScope;
  available: boolean;
  value: number | null;
  per_ue: Record<string, number> | null;
  unavailable_reason: string | null;
  sample_size: number;
  calculation_method: string;
  source_experiment: string;
  backend: string;
  scenario_id: string;
  seed: number;
  source_type: string;
  measured: boolean;
  assumptions: string[];
  acceptance_kpi: boolean;
}

export interface KpiDefinition {
  id: string;
  version: string;
  name_zh: string;
  name_en: string;
  unit: string;
  scope: KpiScope;
  formula: string;
  measurement_method: string;
  required_inputs: string[];
  source: string;
  assumptions: string[];
  acceptance_kpi: boolean;
  note_zh: string | null;
  doc: string;
}

export interface SystemArtifactView {
  name: string;
  type: string;
  media_type: string;
  description: string | null;
  url: string;
}

export interface SystemExperimentProvenance {
  backend?: string;
  provider?: string | null;
  model_type?: SystemModelType;
  model_label?: string;
  source_type?: string;
  measured?: boolean;
  huawei_data?: boolean;
  acceptance_evidence?: boolean;
  assumptions?: string[];
}

export interface SystemExperimentResponse {
  experiment_id: string;
  name: string;
  experiment_type: 'system';
  purpose: string;
  status: SystemExperimentStatus;
  scenario: { scenario_id: string; name_zh: string; name_en: string };
  backend: {
    id: string;
    version: string | null;
    model_type: SystemModelType | null;
    model_label: string | null;
    source_type: string | null;
  };
  seed: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  result: SystemSimulationResult | null;
  kpis: KpiResult[];
  artifacts: SystemArtifactView[];
  provenance: SystemExperimentProvenance;
  scientific_boundary_zh: string;
  scientific_boundary_en: string;
  error: { code: string; message: string; type: string } | null;
  warnings: string[];
  status_history: { status: SystemExperimentStatus; at: string }[];
}

export interface SystemExperimentList {
  items: SystemExperimentResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface SystemExperimentCreateRequest {
  name: string;
  scenario_id: string;
  backend_id?: string;
}
