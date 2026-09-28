import type {
  AlgorithmRunInfo,
  AlgorithmTrace,
  EvaluationBudget,
  EvidenceDescriptor,
  HyperparameterDefinition,
  HyperparameterValue,
  ParameterSpec,
  StopReason,
} from './algorithm';
import type { CandidateError, ObjectiveDirection, ObjectiveEvaluation, OptimizationStatus } from './optimization';

export type ParameterValue = number | string | number[];
export type ParameterRole = 'optimization_variable' | 'algorithm_hyperparameter';
export type ParameterType = 'continuous' | 'integer' | 'discrete' | 'categorical' | 'vector';

export interface ParameterBounds {
  lower: number;
  upper: number;
  lower_inclusive: boolean;
  upper_inclusive: boolean;
}

export interface ParameterDefinition {
  id: string;
  name_zh: string;
  name_en: string;
  role: ParameterRole;
  type: ParameterType;
  unit: string;
  default: ParameterValue | null;
  bounds: ParameterBounds | null;
  choices: ParameterValue[] | null;
  vector_length: number | null;
  shape?: number[] | null;
  element_type?: 'float' | 'integer' | null;
  constraints: string[];
  value_generation: string[];
  source: string;
  description_zh: string;
  description_en: string;
}

export interface SystemOptimizerView {
  id: string;
  name_zh: string;
  name_en: string;
  category: string;
  learning_algorithm: boolean;
  description_zh: string;
  description_en: string;
  supported_problem_types: string[];
  hyperparameters: HyperparameterDefinition[];
}

export interface SystemObjectiveView {
  id: string;
  version: string;
  direction: ObjectiveDirection;
  name_zh: string;
  name_en: string;
  input_kpis: string[];
  formula: string;
  unit: string;
  required_experiment_type: string;
  required_capabilities: string[];
  description_zh: string;
  description_en: string;
  assumptions: string[];
  limitations: string[];
  acceptance_kpi: boolean;
  measured_data: boolean;
  huawei_data: boolean;
  document: string;
}

export interface SystemParameterView {
  definition: ParameterDefinition;
  affects_propagation: boolean;
  recommended_values: number[];
  recommended_values_source: string;
  recommended_search_bounds: number[];
  recommended_search_bounds_source: string;
}

export interface ObservedVariability {
  kpi_id: string;
  relative_percent: number;
  description_zh: string;
  description_en: string;
  source: string;
}

export interface BenchmarkProtocol {
  protocol_id: string;
  version: string;
  name_zh: string;
  name_en: string;
  num_repeats: number;
  simulation_slots: number;
  warmup_slots: number;
  aggregation_method: 'single_run' | 'mean';
  common_channel: boolean;
  common_ue_population: boolean;
  common_traffic: boolean;
  seed_policy: string;
  observed_variability: ObservedVariability;
  rationale: string[];
  limitations: string[];
  frozen_at: string;
  document: string;
  evidence: string;
}

export interface UePopulationEntry {
  ue_id: string;
  serving_cell_id: string;
  position: number[];
}

export interface CommonEvaluationContext {
  context_id: string;
  scenario_id: string;
  scenario_version: string;
  seed: number;
  ue_population: {
    ue_population_id: string;
    sha256: string;
    seed: number;
    ues: UePopulationEntry[];
  };
  traffic_realization: { traffic_realization_id: string; sha256: string; model: Record<string, unknown> };
  channel_realization: {
    channel_realization_id: string;
    sha256: string;
    hash_rule: string;
    artifact: string;
    arrays: Record<string, { shape: number[]; dtype: string }>;
    size_bytes: number;
    source_scenario_id: string;
    seed: number;
    provider: string;
    provider_versions: Record<string, string | null>;
    propagation_fingerprint: string;
    mean_channel_gain_db: Record<string, number>;
    created_at: string;
  };
  simulation_horizon: { num_slots: number; warmup_slots: number; slot_duration_s: number; measured_duration_s: number };
  backend_id: string;
  backend_version: string | null;
  scheduler_config: Record<string, unknown>;
  link_adaptation_config: Record<string, unknown>;
  power_control_config: Record<string, unknown>;
  benchmark_protocol_id: string;
  benchmark_protocol_version: string;
  created_at: string;
}

export interface KpiStatistic {
  mean: number;
  std: number;
  min: number;
  max: number;
  n: number;
}

export interface FairnessEvidence {
  evaluation_context_id: string;
  ue_population_sha256: string;
  channel_realization_id: string;
  channel_sha256: string;
  traffic_realization_id: string;
  traffic_sha256: string;
  num_slots: number;
  warmup_slots: number;
  backend_id: string;
  backend_version: string | null;
  channel_reused: boolean;
}

export interface SystemOptimizationCandidate {
  candidate_id: string;
  iteration: number;
  parameters: Record<string, number>;
  status: 'evaluated' | 'failed';
  experiment_id: string | null;
  is_baseline: boolean;
  reused_baseline: boolean;
  objective: ObjectiveEvaluation | null;
  runtime_seconds: number | null;
  error: CandidateError | null;
  evaluation_context_id: string | null;
  experiment_ids: string[];
  network_throughput_mbps: KpiStatistic | null;
  average_ue_throughput_mbps: KpiStatistic | null;
  p5_ue_throughput_mbps: KpiStatistic | null;
  per_ue_throughput_mbps: Record<string, number>;
  fairness: FairnessEvidence | null;
  algorithm_round?: number | null;
  evaluation_cache_key?: string | null;
  cache_hit?: boolean;
  reused_candidate_id?: string | null;
}

export type KpiDirection = 'increase' | 'decrease' | 'unchanged';

export interface KpiChange {
  kpi_id: string;
  baseline: number;
  best: number;
  absolute_change: number;
  relative_change_percent: number | null;
  direction: KpiDirection;
}

export interface SystemComparison {
  baseline_candidate_id: string;
  best_candidate_id: string;
  baseline_experiment_id: string;
  best_experiment_id: string;
  baseline_parameters: Record<string, number>;
  best_parameters: Record<string, number>;
  baseline_objective: number;
  best_objective: number;
  absolute_improvement: number;
  relative_improvement_percent: number | null;
  improved: boolean;
  kpi_changes: KpiChange[];
  negative_kpi_changes: string[];
  within_observed_variability: boolean;
  observed_variability_percent: number;
  tie_break_rule: string;
}

export interface FairnessCheck {
  id: string;
  label_zh: string;
  label_en: string;
  passed: boolean;
  detail: string;
}

export type SystemOptimizationStage =
  | 'created'
  | 'preparing_context'
  | 'running_baseline'
  | 'evaluating_candidate'
  | 'selecting_best'
  | 'persisting_evidence'
  | 'completed'
  | 'failed';

export interface SystemOptimizationProgress {
  stage: SystemOptimizationStage;
  completed_candidates: number;
  total_candidates: number;
  current_candidate_id: string | null;
  current_parameter_value: number | null;
}

export interface SystemOptimizationArtifactLink {
  name: string;
  media_type: string;
  description: string;
  url: string;
}

export interface SystemOptimizationResponse {
  optimization_id: string;
  name: string;
  problem_type: 'system';
  status: OptimizationStatus;
  scenario_id: string;
  scenario_name_zh: string;
  scenario_name_en: string;
  backend_id: string;
  optimizer_id: string;
  optimizer_version: string;
  objective: { id: string; version: string; direction: ObjectiveDirection; params: Record<string, number> };
  parameter: ParameterDefinition;
  candidate_values: number[];
  algorithm_hyperparameters: Record<string, HyperparameterValue>;
  baseline_parameters: Record<string, number>;
  benchmark_protocol: BenchmarkProtocol;
  seed: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  evaluation_context: CommonEvaluationContext | null;
  baseline: SystemOptimizationCandidate | null;
  candidates: SystemOptimizationCandidate[];
  best_candidate_id: string | null;
  comparison: SystemComparison | null;
  fairness: { fair: boolean; checks: FairnessCheck[] } | null;
  progress: SystemOptimizationProgress;
  runtime: {
    context_seconds: number | null;
    baseline_seconds: number | null;
    candidate_evaluation_seconds: number | null;
    total_seconds: number | null;
  };
  provenance: Record<string, unknown>;
  warnings: string[];
  error: { code: string; message: string; type: string; failed_candidate_id: string | null } | null;
  events: { event: string; at: string; candidate_id: string | null; experiment_id: string | null }[];
  status_history: { status: OptimizationStatus; at: string }[];
  artifact_links: SystemOptimizationArtifactLink[];
  scientific_boundary_zh: string;
  scientific_boundary_en: string;
  optimizer_notice_zh: string;
  optimizer_notice_en: string;
  evidence_descriptor?: EvidenceDescriptor | null;
  algorithm?: AlgorithmRunInfo | null;
  parameter_space?: { parameters: ParameterDefinition[]; constraints: unknown[]; metadata: Record<string, unknown> } | null;
  evaluation_budget?: EvaluationBudget | null;
  algorithm_trace?: AlgorithmTrace | null;
  stop_reason?: StopReason | null;
  recommendation_matches_best?: boolean | null;
}

export interface SystemOptimizationList {
  items: SystemOptimizationResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface SystemOptimizationCreateRequest {
  problem_type: 'system';
  name: string;
  scenario_id: string;
  algorithm_id: string;
  objective_id: string;
  parameter_space: { parameters: ParameterSpec[] };
  algorithm_hyperparameters: Record<string, HyperparameterValue>;
  evaluation_budget?: { max_evaluations: number };
  benchmark_protocol_id: string;
}
