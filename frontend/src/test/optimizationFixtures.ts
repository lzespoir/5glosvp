/**
 * 前端单元测试夹具（TEST FIXTURE）：数值为手工构造，仅用于验证 UI 渲染逻辑，
 * 不是仿真结果，也不得作为优化效果证据。
 */
import type { ObjectiveView, OptimizationCandidate, OptimizationResponse, OptimizerView } from '../types/optimization';

export const fixtureOptimizer: OptimizerView = {
  id: 'grid_search',
  name_zh: '网格搜索',
  name_en: 'Grid Search',
  category: 'engineering_baseline',
  learning_algorithm: false,
  available: true,
  description_zh: '穷举评价',
  description_en: 'Exhaustive evaluation',
  supported_parameters: [{ id: 'tx_power_dbm', name_zh: '发射功率', name_en: 'TX Power', unit: 'dBm' }],
  recommended_parameter_space: { tx_power_dbm: [38, 40, 42, 44, 46] },
  recommended_parameter_space_source: '[A] Assumption',
  max_candidates: 10,
};

export const fixtureObjective: ObjectiveView = {
  id: 'PROPAGATION_UTILITY_V0_1',
  version: '0.1',
  name_zh: '传播层效用',
  name_en: 'Propagation Utility',
  direction: 'maximize',
  description_zh: '传播层工程目标函数',
  description_en: 'Propagation-level engineering objective',
  formula: 'J = C_sinr - λ·c_P',
  required_metrics: ['sinr'],
  default_params: { lambda_power: 0.1 },
  assumptions: { lambda_power: '[A]' },
};

function candidate(
  id: string,
  iteration: number,
  power: number,
  coverage: number,
  experimentId: string,
  extra: Partial<OptimizationCandidate> = {},
): OptimizationCandidate {
  const cost = (power - 38) / 8;
  return {
    candidate_id: id,
    iteration,
    parameters: { tx_power_dbm: power },
    status: 'evaluated',
    experiment_id: experimentId,
    is_baseline: false,
    reused_baseline: false,
    objective: {
      objective_id: 'PROPAGATION_UTILITY_V0_1',
      objective_version: '0.1',
      value: coverage - 0.1 * cost,
      components: {
        sinr_coverage_ratio: coverage,
        sinr_threshold_db: 0,
        covered_cells: Math.round(coverage * 100),
        num_cells: 100,
        tx_power_dbm: power,
        power_min_dbm: 38,
        power_max_dbm: 46,
        normalized_power_cost: cost,
        lambda_power: 0.1,
        power_cost_term: 0.1 * cost,
      },
    },
    runtime_seconds: 1.5,
    error: null,
    ...extra,
  };
}

export function fixtureOptimization(overrides: Partial<OptimizationResponse> = {}): OptimizationResponse {
  const baseline = candidate('BASELINE', 0, 44, 0.56, 'EXP-BASE0001', { is_baseline: true, iteration: 0 });
  const candidates = [
    candidate('CAND-001', 1, 38, 0.55, 'EXP-CAND0001'),
    candidate('CAND-002', 2, 40, 0.553, 'EXP-CAND0002'),
    candidate('CAND-003', 3, 44, 0.56, 'EXP-BASE0001', { reused_baseline: true, runtime_seconds: 0 }),
  ];
  const best = candidates[0] as OptimizationCandidate;
  const bValue = baseline.objective?.value ?? 0;
  const oValue = best.objective?.value ?? 0;
  return {
    optimization_id: 'OPT-AAAA0001',
    name: 'fixture',
    status: 'succeeded',
    scenario: { scenario_id: 'SIONNA-DEMO-001', name_zh: '内置场景', name_en: 'Built-in Scene' },
    simulation_backend: 'sionna_rt',
    optimizer: { id: 'grid_search', name_zh: '网格搜索', name_en: 'Grid Search', category: 'engineering_baseline', learning_algorithm: false },
    objective: {
      id: 'PROPAGATION_UTILITY_V0_1',
      version: '0.1',
      direction: 'maximize',
      params: { lambda_power: 0.1 },
      name_zh: '传播层效用',
      name_en: 'Propagation Utility',
      formula: 'J = C_sinr - λ·c_P',
    },
    parameter_space: { tx_power_dbm: [38, 40, 44] },
    baseline_parameters: { tx_power_dbm: 44 },
    seed: 42,
    created_at: '2026-09-28T04:00:00+00:00',
    started_at: '2026-09-28T04:00:00+00:00',
    finished_at: '2026-09-28T04:00:10+00:00',
    baseline,
    candidates,
    best_candidate: best,
    comparison: {
      baseline_experiment_id: 'EXP-BASE0001',
      optimized_experiment_id: 'EXP-CAND0001',
      optimized_candidate_id: 'CAND-001',
      baseline_parameters: { tx_power_dbm: 44 },
      optimized_parameters: { tx_power_dbm: 38 },
      baseline_objective: bValue,
      optimized_objective: oValue,
      absolute_improvement: oValue - bValue,
      relative_improvement_percent: ((oValue - bValue) / Math.abs(bValue)) * 100,
    },
    improvement_status: 'improved',
    runtime: { baseline_seconds: 1.5, candidate_evaluation_seconds: 3, total_seconds: 4.6 },
    provenance: {
      optimizer: 'grid_search',
      learning_algorithm: false,
      simulation_backend: 'sionna_rt',
      source_type: 'simulation',
      measured: false,
      objective_id: 'PROPAGATION_UTILITY_V0_1',
      objective_version: '0.1',
      evidence_level: 'Synthetic / Simulation Validation',
      search_space_source: '[A] Assumption',
    },
    error: null,
    events: [
      { event: 'optimization_created', at: '2026-09-28T04:00:00+00:00', candidate_id: null, experiment_id: null },
      { event: 'baseline_evaluated', at: '2026-09-28T04:00:02+00:00', candidate_id: 'BASELINE', experiment_id: 'EXP-BASE0001' },
      { event: 'optimization_completed', at: '2026-09-28T04:00:10+00:00', candidate_id: null, experiment_id: null },
    ],
    status_history: [
      { status: 'created', at: '2026-09-28T04:00:00+00:00' },
      { status: 'running', at: '2026-09-28T04:00:00+00:00' },
      { status: 'succeeded', at: '2026-09-28T04:00:10+00:00' },
    ],
    ...overrides,
  };
}
