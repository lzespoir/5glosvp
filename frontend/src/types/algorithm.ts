import type { ParameterBounds, ParameterType } from './systemOptimization';

export type AlgorithmCategory = 'engineering_baseline' | 'research_demo' | 'research' | 'external';
export type AlgorithmStatus = 'available' | 'experimental' | 'deprecated';
export type HyperparameterType = 'float' | 'integer' | 'boolean' | 'categorical';
export type HyperparameterValue = boolean | number | string;
export type StopReason =
  | 'completed'
  | 'max_iterations'
  | 'converged'
  | 'no_improvement'
  | 'budget_exhausted'
  | 'failed'
  | 'cancelled';
export type CompatibilityCode =
  | 'ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED'
  | 'ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED'
  | 'ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED'
  | 'ALGORITHM_CONSTRAINTS_NOT_SUPPORTED'
  | 'ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED'
  | 'INVALID_HYPERPARAMETER'
  | 'INVALID_EVALUATION_BUDGET';

export interface AlgorithmCapabilities {
  supports_discrete: boolean;
  supports_continuous: boolean;
  supports_integer: boolean;
  supports_categorical: boolean;
  supports_vector: boolean;
  supports_constraints: boolean;
  supports_multi_objective: boolean;
  supports_batch_suggestions: boolean;
  supports_iterative_feedback: boolean;
  supports_auto_configuration: boolean;
  max_parameters: number | null;
}

export interface HyperparameterDefinition {
  id: string;
  name_zh: string;
  name_en: string;
  type: HyperparameterType;
  default: HyperparameterValue;
  bounds: ParameterBounds | null;
  choices: HyperparameterValue[] | null;
  unit: string;
  description_zh: string;
  description_en: string;
}

export interface AlgorithmSummary {
  id: string;
  name_zh: string;
  name_en: string;
  version: string;
  category: AlgorithmCategory;
  learning_algorithm: boolean;
  project_research_deliverable: boolean;
  capabilities: AlgorithmCapabilities;
  supported_parameter_types: ParameterType[];
  supported_problem_types: string[];
  auto_configuration: boolean;
  status: AlgorithmStatus;
  sdk_version: string;
  purpose_zh: string;
  purpose_en: string;
  labels: string[];
  notice_zh: string;
  notice_en: string;
}

export interface AlgorithmList {
  sdk_version: string;
  items: AlgorithmSummary[];
  integration_contract: string;
  integration_guide: string;
}

export interface AlgorithmMetadata {
  algorithm_id: string;
  name_zh: string;
  name_en: string;
  version: string;
  category: AlgorithmCategory;
  description_zh: string;
  description_en: string;
  purpose_zh: string;
  purpose_en: string;
  provider: string;
  learning_algorithm: boolean;
  project_research_deliverable: boolean;
  acceptance_algorithm: boolean;
  capabilities: AlgorithmCapabilities;
  hyperparameter_schema: HyperparameterDefinition[];
  supported_problem_types: string[];
  source: string;
  status: AlgorithmStatus;
  sdk_version: string;
  labels: string[];
  supported_parameter_types: ParameterType[];
  auto_configuration: boolean;
}

export interface AlgorithmEvidenceStatus {
  optimization_runs: number;
  succeeded_runs: number;
  latest_optimization_id: string | null;
  latest_succeeded_optimization_id: string | null;
  acceptance_eligible_runs: number;
}

export interface AlgorithmDetail {
  metadata: AlgorithmMetadata;
  notice_zh: string;
  notice_en: string;
  evidence: AlgorithmEvidenceStatus;
  integration_contract: string;
  integration_guide: string;
}

export interface ParameterSpec {
  id: string;
  type: 'continuous' | 'discrete';
  lower?: number | null;
  upper?: number | null;
  choices?: number[] | null;
}

export interface CompatibilityIssue {
  code: CompatibilityCode;
  message: string;
  parameter_id: string | null;
}

export interface AlgorithmValidateRequest {
  problem_type: 'system';
  scenario_id?: string;
  objective_id: string;
  parameter_space: { parameters: ParameterSpec[] };
  algorithm_hyperparameters: Record<string, HyperparameterValue>;
  evaluation_budget?: { max_evaluations: number };
}

export interface CompatibilityReport {
  algorithm_id: string;
  compatible: boolean;
  errors: CompatibilityIssue[];
  warnings: string[];
  resolved_hyperparameters: Record<string, HyperparameterValue> | null;
}

export interface TraceEvaluation {
  sequence: number;
  round: number;
  candidate_id: string;
  parameters: Record<string, number>;
  objective: number | null;
  secondary_metrics: Record<string, number>;
  status: string;
  cache_hit: boolean;
  best_so_far_candidate_id: string | null;
  best_so_far_objective: number | null;
  at: string;
}

export interface TraceRound {
  round: number;
  state_before: Record<string, unknown>;
  suggestions: Record<string, number>[];
  evaluated_candidate_ids: string[];
  rejected_suggestions: Record<string, number>[];
  state_after: Record<string, unknown>;
}

export interface AlgorithmTrace {
  algorithm_id: string;
  algorithm_version: string;
  sdk_version: string;
  hyperparameters: Record<string, HyperparameterValue>;
  max_evaluations: number;
  initial_state: Record<string, unknown>;
  evaluations: TraceEvaluation[];
  rounds: TraceRound[];
  evaluations_used: number;
  rejected_suggestions: number;
  stop_reason: StopReason | null;
  stop_detail: string;
  recommendation: { parameters: Record<string, number> | null; note: string } | null;
  final_state: Record<string, unknown>;
  error: string | null;
}

export interface EvaluationBudget {
  max_evaluations: number;
  evaluations_used: number;
  simulations_run: number;
  cache_hits: number;
  rejected_suggestions: number;
}

export interface AlgorithmRunInfo {
  algorithm_id: string;
  algorithm_version: string;
  algorithm_name_en: string;
  algorithm_name_zh: string;
  algorithm_provider: string;
  algorithm_category: AlgorithmCategory;
  sdk_version: string;
  learning_algorithm: boolean;
  project_research_deliverable: boolean;
  purpose_en: string;
  purpose_zh: string;
  hyperparameters: Record<string, HyperparameterValue>;
  auto_configured: boolean;
  algorithm_config_hash: string;
  parameter_space_hash: string;
  source: string;
  source_revision: Record<string, string | null>;
}

export type VerificationStatus =
  | 'not_verified'
  | 'platform_checks_passed'
  | 'platform_checks_failed'
  | 'independently_verified'
  | 'independent_verification_failed';

export type AcceptanceIneligibilityReason =
  | 'simulation_only'
  | 'not_measured'
  | 'not_huawei_data'
  | 'unconfirmed_acceptance_kpi'
  | 'engineering_baseline'
  | 'integration_demo_algorithm'
  | 'test_fixture'
  | 'not_succeeded';

export interface EvidenceDescriptor {
  evidence_id: string;
  evidence_type: 'system_optimization' | 'algorithm_optimization';
  source_entity_type: string;
  source_entity_id: string;
  created_at: string;
  provenance: Record<string, unknown>;
  verification_status: VerificationStatus;
  verification_detail: string;
  acceptance_eligible: boolean;
  acceptance_reason: AcceptanceIneligibilityReason[];
  artifacts: { name: string; media_type: string; location: string }[];
  verified: boolean;
}

export interface EvidenceList {
  items: EvidenceDescriptor[];
  total: number;
}
