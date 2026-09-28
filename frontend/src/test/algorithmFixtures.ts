import type {
  AlgorithmCapabilities,
  AlgorithmDetail,
  AlgorithmList,
  AlgorithmSummary,
  AlgorithmTrace,
  CompatibilityReport,
  EvidenceDescriptor,
  HyperparameterDefinition,
} from '../types/algorithm';
import type { SystemOptimizationResponse } from '../types/systemOptimization';
import { betaDefinition, candidate, fixtureSystemOptimization } from './systemOptimizationFixtures';

const CAPS: AlgorithmCapabilities = {
  supports_discrete: false,
  supports_continuous: false,
  supports_integer: false,
  supports_categorical: false,
  supports_vector: false,
  supports_constraints: false,
  supports_multi_objective: false,
  supports_batch_suggestions: true,
  supports_iterative_feedback: false,
  supports_auto_configuration: true,
  max_parameters: 1,
};

export const gridSummary: AlgorithmSummary = {
  id: 'grid_search',
  name_zh: '网格搜索',
  name_en: 'Grid Search',
  version: '0.2',
  category: 'engineering_baseline',
  learning_algorithm: false,
  project_research_deliverable: false,
  capabilities: { ...CAPS, supports_discrete: true },
  supported_parameter_types: ['discrete'],
  supported_problem_types: ['propagation', 'system'],
  auto_configuration: true,
  status: 'available',
  sdk_version: '0.1',
  purpose_zh: '工程基线',
  purpose_en: 'Engineering baseline',
  labels: ['Engineering Baseline'],
  notice_zh: 'Grid Search 为工程基线优化器，不属于项目学习优化算法。',
  notice_en: 'Grid Search is an engineering baseline optimizer.',
};

export const demoSummary: AlgorithmSummary = {
  id: 'research_demo_optimizer',
  name_zh: 'Research Demo Optimizer（自适应局部搜索）',
  name_en: 'Research Demo Optimizer (Adaptive Local Search)',
  version: '0.1.0',
  category: 'research_demo',
  learning_algorithm: false,
  project_research_deliverable: false,
  capabilities: { ...CAPS, supports_continuous: true, supports_iterative_feedback: true },
  supported_parameter_types: ['continuous'],
  supported_problem_types: ['system'],
  auto_configuration: true,
  status: 'experimental',
  sdk_version: '0.1',
  purpose_zh: '算法接入验证（Integration Demo）',
  purpose_en: 'Algorithm Integration Validation',
  labels: ['Integration Demo', '接入验证算法', 'Not Project Research Deliverable'],
  notice_zh: 'Research Demo Optimizer 为算法接入验证算法，不是项目科研成果，也不是学习优化算法。',
  notice_en: 'Research Demo Optimizer is an algorithm-integration validation algorithm.',
};

export const algorithmList: AlgorithmList = {
  sdk_version: '0.1',
  items: [gridSummary, demoSummary],
  integration_contract: 'docs/algorithms/algorithm-integration-contract-v0.1.md',
  integration_guide: 'docs/algorithms/how-to-integrate-an-algorithm.md',
};

const openUnit = { lower: 0, upper: 1, lower_inclusive: false, upper_inclusive: true };

export const demoSchema: HyperparameterDefinition[] = [
  { id: 'initial_step', name_zh: '初始步长', name_en: 'Initial Step', type: 'float', default: 0.2, bounds: openUnit,
    choices: null, unit: '1', description_zh: '首轮邻点距离', description_en: '' },
  { id: 'max_iterations', name_zh: '最大迭代轮数', name_en: 'Max Iterations', type: 'integer', default: 8,
    bounds: { lower: 1, upper: 50, lower_inclusive: true, upper_inclusive: true }, choices: null, unit: '1',
    description_zh: '', description_en: '' },
  { id: 'start_point', name_zh: '起点', name_en: 'Start Point', type: 'categorical', default: 'baseline', bounds: null,
    choices: ['baseline', 'center'], unit: '1', description_zh: '', description_en: '' },
];

function detail(s: AlgorithmSummary, schema: HyperparameterDefinition[]): AlgorithmDetail {
  return {
    metadata: {
      algorithm_id: s.id, name_zh: s.name_zh, name_en: s.name_en, version: s.version, category: s.category,
      description_zh: '描述', description_en: 'description', purpose_zh: s.purpose_zh, purpose_en: s.purpose_en,
      provider: '5GLOSVP platform', learning_algorithm: false, project_research_deliverable: false,
      acceptance_algorithm: false, capabilities: s.capabilities, hyperparameter_schema: schema,
      supported_problem_types: s.supported_problem_types, source: `src/algorithms/${s.id}.py`, status: s.status,
      sdk_version: '0.1', labels: s.labels, supported_parameter_types: s.supported_parameter_types,
      auto_configuration: true,
    },
    notice_zh: s.notice_zh,
    notice_en: s.notice_en,
    evidence: { optimization_runs: 1, succeeded_runs: 1, latest_optimization_id: 'OPT-DEMO0001',
      latest_succeeded_optimization_id: 'OPT-DEMO0001', acceptance_eligible_runs: 0 },
    integration_contract: algorithmList.integration_contract,
    integration_guide: algorithmList.integration_guide,
  };
}

export const gridDetail = detail(gridSummary, []);
export const demoDetail = detail(demoSummary, demoSchema);

export function compatible(algorithmId: string): CompatibilityReport {
  return { algorithm_id: algorithmId, compatible: true, errors: [], warnings: [], resolved_hyperparameters: {} };
}

export const evidenceDescriptor: EvidenceDescriptor = {
  evidence_id: 'EVD-OPT-DEMO0001',
  evidence_type: 'algorithm_optimization',
  source_entity_type: 'system_optimization',
  source_entity_id: 'OPT-DEMO0001',
  created_at: '2026-09-28T10:00:00Z',
  provenance: { algorithm: 'research_demo_optimizer' },
  verification_status: 'platform_checks_passed',
  verification_detail: 'fairness checks passed',
  acceptance_eligible: false,
  acceptance_reason: ['simulation_only', 'not_measured', 'not_huawei_data', 'unconfirmed_acceptance_kpi',
    'integration_demo_algorithm'],
  artifacts: [],
  verified: false,
};

const demoTrace: AlgorithmTrace = {
  algorithm_id: 'research_demo_optimizer',
  algorithm_version: '0.1.0',
  sdk_version: '0.1',
  hyperparameters: { initial_step: 0.2, max_iterations: 8, start_point: 'baseline' },
  max_evaluations: 8,
  initial_state: { mode: 'explore', incumbent: 0.9, step: 0.2 },
  evaluations: [
    { sequence: 0, round: 0, candidate_id: 'BASELINE', parameters: { scheduler_beta: 0.9 }, objective: 131.14,
      secondary_metrics: {}, status: 'evaluated', cache_hit: false, best_so_far_candidate_id: 'BASELINE',
      best_so_far_objective: 131.14, at: '' },
    { sequence: 1, round: 1, candidate_id: 'CAND-001', parameters: { scheduler_beta: 0.7 }, objective: 200.5,
      secondary_metrics: {}, status: 'evaluated', cache_hit: false, best_so_far_candidate_id: 'CAND-001',
      best_so_far_objective: 200.5, at: '' },
    { sequence: 2, round: 1, candidate_id: 'CAND-002', parameters: { scheduler_beta: 0.99 }, objective: 120.1,
      secondary_metrics: {}, status: 'evaluated', cache_hit: false, best_so_far_candidate_id: 'CAND-001',
      best_so_far_objective: 200.5, at: '' },
  ],
  rounds: [
    { round: 1, state_before: { mode: 'explore', incumbent: 0.9, step: 0.2 }, suggestions: [{ scheduler_beta: 0.7 },
      { scheduler_beta: 0.99 }], evaluated_candidate_ids: ['CAND-001', 'CAND-002'], rejected_suggestions: [],
      state_after: { mode: 'extend', incumbent: 0.7, step: 0.2, last_decision: 'move 0.9 → 0.7 (improved)' } },
  ],
  evaluations_used: 2,
  rejected_suggestions: 0,
  stop_reason: 'budget_exhausted',
  stop_detail: 'platform budget of 2 evaluations used',
  recommendation: { parameters: { scheduler_beta: 0.7 }, note: '' },
  final_state: {},
  error: null,
};

export function fixtureDemoOptimization(overrides: Partial<SystemOptimizationResponse> = {}): SystemOptimizationResponse {
  const baseline = candidate('BASELINE', 0, 0.9, 131.14, 12.54);
  return fixtureSystemOptimization({
    optimization_id: 'OPT-DEMO0001',
    optimizer_id: 'research_demo_optimizer',
    optimizer_version: '0.1.0',
    candidate_values: [],
    algorithm_hyperparameters: demoTrace.hyperparameters,
    baseline,
    candidates: [
      candidate('CAND-001', 1, 0.7, 200.5, 11.0, { algorithm_round: 1 }),
      candidate('CAND-002', 2, 0.99, 120.1, 12.0, { algorithm_round: 1 }),
    ],
    best_candidate_id: 'CAND-001',
    comparison: null,
    optimizer_notice_zh: demoSummary.notice_zh,
    optimizer_notice_en: demoSummary.notice_en,
    algorithm: {
      algorithm_id: 'research_demo_optimizer', algorithm_version: '0.1.0', algorithm_name_en: demoSummary.name_en,
      algorithm_name_zh: demoSummary.name_zh, algorithm_provider: '5GLOSVP platform', algorithm_category: 'research_demo',
      sdk_version: '0.1', learning_algorithm: false, project_research_deliverable: false,
      purpose_en: demoSummary.purpose_en, purpose_zh: demoSummary.purpose_zh, hyperparameters: demoTrace.hyperparameters,
      auto_configured: true, algorithm_config_hash: 'a'.repeat(64), parameter_space_hash: 'b'.repeat(64),
      source: 'src/algorithms/examples/research_demo_optimizer/algorithm.py',
      source_revision: { type: 'git_commit', value: 'c'.repeat(40) },
    },
    parameter_space: {
      parameters: [{ ...betaDefinition, bounds: { lower: 0.05, upper: 0.99, lower_inclusive: true, upper_inclusive: true } }],
      constraints: [],
      metadata: {},
    },
    evaluation_budget: { max_evaluations: 2, evaluations_used: 2, simulations_run: 2, cache_hits: 0, rejected_suggestions: 0 },
    algorithm_trace: demoTrace,
    stop_reason: 'budget_exhausted',
    recommendation_matches_best: true,
    evidence_descriptor: evidenceDescriptor,
    ...overrides,
  });
}
