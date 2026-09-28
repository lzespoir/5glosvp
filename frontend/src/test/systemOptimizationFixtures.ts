import type {
  BenchmarkProtocol,
  KpiStatistic,
  ParameterDefinition,
  SystemObjectiveView,
  SystemOptimizationCandidate,
  SystemOptimizationResponse,
  SystemOptimizerView,
  SystemParameterView,
} from '../types/systemOptimization';

export const OPT_ID = 'OPT-5Y5OPT01';

export const betaDefinition: ParameterDefinition = {
  id: 'scheduler_beta',
  name_zh: 'PF 调度折扣因子 β',
  name_en: 'PF Scheduler Discount Factor β',
  role: 'optimization_variable',
  type: 'continuous',
  unit: '1',
  default: 0.98,
  bounds: { lower: 0, upper: 1, lower_inclusive: false, upper_inclusive: false },
  choices: null,
  vector_length: null,
  constraints: [],
  value_generation: ['enumerated', 'algorithm_generated'],
  source: 'Sionna PFSchedulerSUMIMO',
  description_zh: '',
  description_en: '',
};

export function fixtureProtocol(overrides: Partial<BenchmarkProtocol> = {}): BenchmarkProtocol {
  return {
    protocol_id: 'SYSTEM_BENCHMARK_V0_1',
    version: '0.1',
    name_zh: '系统级公平评价协议 V0.1',
    name_en: 'System Benchmark Protocol V0.1',
    num_repeats: 1,
    simulation_slots: 500,
    warmup_slots: 0,
    aggregation_method: 'single_run',
    common_channel: true,
    common_ue_population: true,
    common_traffic: true,
    seed_policy: 'fixed',
    observed_variability: {
      kpi_id: 'NETWORK_THROUGHPUT_V0_1',
      relative_percent: 6.9,
      description_zh: '三次独立运行',
      description_en: 'three runs',
      source: 'reference',
    },
    rationale: [],
    limitations: ['one scenario'],
    frozen_at: '2026-09-28',
    document: 'docs/benchmark/system-benchmark-v0.1.md',
    evidence: 'reference/day6_horizon_study/',
    ...overrides,
  };
}

export const fixtureOptimizer: SystemOptimizerView = {
  id: 'grid_search',
  name_zh: '网格搜索',
  name_en: 'Grid Search',
  category: 'engineering_baseline',
  learning_algorithm: false,
  description_zh: '',
  description_en: '',
  supported_problem_types: ['propagation', 'system'],
  hyperparameters: [],
};

export const fixtureObjective: SystemObjectiveView = {
  id: 'NETWORK_THROUGHPUT_MAX_V0_1',
  version: '0.1',
  direction: 'maximize',
  name_zh: '网络吞吐率最大化',
  name_en: 'Network Throughput Maximization',
  input_kpis: ['NETWORK_THROUGHPUT_V0_1'],
  formula: 'J = NETWORK_THROUGHPUT_V0_1   (maximize)',
  unit: 'Mbps',
  required_experiment_type: 'system',
  required_capabilities: ['channel_reuse'],
  description_zh: '',
  description_en: '',
  assumptions: [],
  limitations: [],
  acceptance_kpi: false,
  measured_data: false,
  huawei_data: false,
  document: 'docs/objectives/network-throughput-max-v0.1.md',
};

export const fixtureParameter: SystemParameterView = {
  definition: betaDefinition,
  affects_propagation: false,
  recommended_values: [0.1, 0.3, 0.6, 0.9, 0.99],
  recommended_values_source: '[A] Demo search space',
};

function stat(mean: number): KpiStatistic {
  return { mean, std: 0, min: mean, max: mean, n: 1 };
}

export function candidate(
  id: string,
  iteration: number,
  beta: number,
  net: number,
  p5: number,
  overrides: Partial<SystemOptimizationCandidate> = {},
): SystemOptimizationCandidate {
  const exp = `EXP-${id.replace('-', '')}`;
  return {
    candidate_id: id,
    iteration,
    parameters: { scheduler_beta: beta },
    status: 'evaluated',
    experiment_id: exp,
    is_baseline: iteration === 0,
    reused_baseline: false,
    objective: { objective_id: 'NETWORK_THROUGHPUT_MAX_V0_1', objective_version: '0.1', value: net, components: {} },
    runtime_seconds: 97,
    error: null,
    evaluation_context_id: 'CTX-00000001',
    experiment_ids: [exp],
    network_throughput_mbps: stat(net),
    average_ue_throughput_mbps: stat(net / 6),
    p5_ue_throughput_mbps: stat(p5),
    per_ue_throughput_mbps: { 'UE-001': p5, 'UE-002': net - p5 },
    fairness: null,
    ...overrides,
  };
}

export function fixtureSystemOptimization(overrides: Partial<SystemOptimizationResponse> = {}): SystemOptimizationResponse {
  const baseline = candidate('BASELINE', 0, 0.9, 131.14, 12.54);
  const best = candidate('CAND-002', 2, 0.3, 236.35, 10.29);
  return {
    optimization_id: OPT_ID,
    name: 'demo',
    problem_type: 'system',
    status: 'succeeded',
    scenario_id: 'SYSTEM-DEMO-001',
    scenario_name_zh: '多用户下行系统仿真演示',
    scenario_name_en: 'Multi-UE Demo',
    backend_id: 'sionna_system',
    optimizer_id: 'grid_search',
    optimizer_version: '0.2',
    objective: { id: 'NETWORK_THROUGHPUT_MAX_V0_1', version: '0.1', direction: 'maximize', params: {} },
    parameter: betaDefinition,
    candidate_values: [0.1, 0.3, 0.99],
    algorithm_hyperparameters: {},
    baseline_parameters: { scheduler_beta: 0.9 },
    benchmark_protocol: fixtureProtocol(),
    seed: 7,
    created_at: '2026-09-28T10:00:00Z',
    started_at: '2026-09-28T10:00:00Z',
    finished_at: '2026-09-28T10:08:00Z',
    evaluation_context: null,
    baseline,
    candidates: [
      candidate('CAND-001', 1, 0.1, 235.66, 10.02),
      best,
      candidate('CAND-003', 3, 0.99, 0, 0, {
        status: 'failed',
        objective: null,
        experiment_ids: [],
        network_throughput_mbps: null,
        average_ue_throughput_mbps: null,
        p5_ue_throughput_mbps: null,
        per_ue_throughput_mbps: {},
        error: { code: 'SIMULATION_FAILED', message: 'boom' },
      }),
    ],
    best_candidate_id: 'CAND-002',
    comparison: {
      baseline_candidate_id: 'BASELINE',
      best_candidate_id: 'CAND-002',
      baseline_experiment_id: 'EXP-BASELINE',
      best_experiment_id: 'EXP-CAND002',
      baseline_parameters: { scheduler_beta: 0.9 },
      best_parameters: { scheduler_beta: 0.3 },
      baseline_objective: 131.14,
      best_objective: 236.35,
      absolute_improvement: 105.21,
      relative_improvement_percent: 80.23,
      improved: true,
      kpi_changes: [
        { kpi_id: 'NETWORK_THROUGHPUT_V0_1', baseline: 131.14, best: 236.35, absolute_change: 105.21, relative_change_percent: 80.23, direction: 'increase' },
        { kpi_id: 'AVG_UE_THROUGHPUT_V0_1', baseline: 21.86, best: 39.39, absolute_change: 17.53, relative_change_percent: 80.23, direction: 'increase' },
        { kpi_id: 'P5_UE_THROUGHPUT_V0_1', baseline: 12.54, best: 10.29, absolute_change: -2.25, relative_change_percent: -17.94, direction: 'decrease' },
      ],
      negative_kpi_changes: ['P5_UE_THROUGHPUT_V0_1'],
      within_observed_variability: false,
      observed_variability_percent: 6.9,
      tie_break_rule: 'baseline value first, then candidate order',
    },
    fairness: {
      fair: true,
      checks: [
        { id: 'same_ue_population', label_zh: '相同 UE', label_en: 'Same UE Population', passed: true, detail: 'UEP' },
        { id: 'same_channel_realization', label_zh: '相同信道', label_en: 'Same Channel Realization', passed: true, detail: 'CH' },
      ],
    },
    progress: { stage: 'completed', completed_candidates: 3, total_candidates: 3, current_candidate_id: null, current_parameter_value: null },
    runtime: { context_seconds: 1, baseline_seconds: 97, candidate_evaluation_seconds: 194, total_seconds: 292 },
    provenance: { optimizer: 'grid_search', learning_algorithm: false, measured: false, huawei_data: false, acceptance_evidence: false },
    warnings: [],
    error: null,
    events: [],
    status_history: [],
    artifact_links: [],
    scientific_boundary_zh: '当前结果来自系统级仿真优化验证，不是华为实测网络优化结果。',
    scientific_boundary_en: 'Results come from system-level simulation optimization validation.',
    optimizer_notice_zh: 'Grid Search 为工程基线优化器，不属于项目学习优化算法。',
    optimizer_notice_en: 'Grid Search is an engineering baseline optimizer.',
    ...overrides,
  };
}
