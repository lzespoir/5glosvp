import type { ScenarioRef } from './experiment';

export type OptimizationStatus = 'created' | 'running' | 'succeeded' | 'failed';
export type ImprovementStatus = 'improved' | 'no_improvement' | 'worse';
export type CandidateStatus = 'evaluated' | 'failed';
export type ObjectiveDirection = 'maximize' | 'minimize';

export interface OptimizerParameter {
  id: string;
  name_zh: string;
  name_en: string;
  unit: string;
}

export interface OptimizerView {
  id: string;
  name_zh: string;
  name_en: string;
  category: string;
  learning_algorithm: boolean;
  available: boolean;
  description_zh: string;
  description_en: string;
  supported_parameters: OptimizerParameter[];
  recommended_parameter_space: Record<string, number[]>;
  recommended_parameter_space_source: string;
  max_candidates: number;
}

export interface ObjectiveView {
  id: string;
  version: string;
  name_zh: string;
  name_en: string;
  direction: ObjectiveDirection;
  description_zh: string;
  description_en: string;
  formula: string;
  required_metrics: string[];
  default_params: Record<string, number>;
  assumptions: Record<string, string>;
}

export interface ObjectiveEvaluation {
  objective_id: string;
  objective_version: string;
  value: number;
  /** 后端计算的目标函数分解，例如 sinr_coverage_ratio / normalized_power_cost / lambda_power */
  components: Record<string, number>;
}

export interface CandidateError {
  code: string;
  message: string;
}

export interface OptimizationCandidate {
  candidate_id: string;
  iteration: number;
  parameters: Record<string, number>;
  status: CandidateStatus;
  experiment_id: string | null;
  is_baseline: boolean;
  reused_baseline: boolean;
  objective: ObjectiveEvaluation | null;
  runtime_seconds: number | null;
  error: CandidateError | null;
}

export interface OptimizationComparison {
  baseline_experiment_id: string;
  optimized_experiment_id: string;
  optimized_candidate_id: string;
  baseline_parameters: Record<string, number>;
  optimized_parameters: Record<string, number>;
  baseline_objective: number;
  optimized_objective: number;
  absolute_improvement: number;
  relative_improvement_percent: number | null;
}

export interface OptimizerRef {
  id: string;
  name_zh: string | null;
  name_en: string | null;
  category: string | null;
  learning_algorithm: boolean | null;
}

export interface ObjectiveRef {
  id: string;
  version: string;
  direction: ObjectiveDirection;
  params: Record<string, number>;
  name_zh: string | null;
  name_en: string | null;
  formula: string | null;
}

export interface OptimizationRuntime {
  baseline_seconds: number | null;
  candidate_evaluation_seconds: number | null;
  total_seconds: number | null;
}

export interface OptimizationEvent {
  event: string;
  at: string;
  candidate_id: string | null;
  experiment_id: string | null;
}

export interface OptimizationErrorView {
  code: string;
  message: string;
  type: string;
  failed_candidate_id: string | null;
  experiment_id: string | null;
}

export interface OptimizationStatusTransition {
  status: OptimizationStatus;
  at: string;
}

export interface OptimizationResponse {
  optimization_id: string;
  name: string;
  status: OptimizationStatus;
  scenario: ScenarioRef;
  simulation_backend: string;
  optimizer: OptimizerRef;
  objective: ObjectiveRef;
  parameter_space: { tx_power_dbm: number[] };
  baseline_parameters: Record<string, number>;
  seed: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  baseline: OptimizationCandidate | null;
  candidates: OptimizationCandidate[];
  best_candidate: OptimizationCandidate | null;
  comparison: OptimizationComparison | null;
  improvement_status: ImprovementStatus | null;
  runtime: OptimizationRuntime;
  provenance: Record<string, unknown>;
  error: OptimizationErrorView | null;
  events: OptimizationEvent[];
  status_history: OptimizationStatusTransition[];
}

export interface OptimizationList {
  items: OptimizationResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface OptimizationCreateRequest {
  name: string;
  scenario_id: string;
  optimizer_id: string;
  objective_id: string;
  parameter_space: { tx_power_dbm: number[] };
  objective_params?: { lambda_power?: number };
}
