import type {
  KpiDirection,
  ParameterDefinition,
  SystemOptimizationCandidate,
  SystemOptimizationProgress,
  SystemOptimizationResponse,
  SystemOptimizationStage,
} from '../types/systemOptimization';
import { EMPTY, isNumber } from './format';
import { AVG_UE_THROUGHPUT, NETWORK_THROUGHPUT, P5_UE_THROUGHPUT } from './system';

export const SCHEDULER_BETA = 'scheduler_beta';
/** 与后端 MAX_SYSTEM_CANDIDATES 一致；后端仍会校验并返回 422。 */
export const MAX_SYSTEM_CANDIDATES = 8;
export const ALLOWED_CLAIM_PREFIX = '在当前冻结仿真协议下，网络吞吐率';
export const NO_IMPROVEMENT_ZH = '当前候选范围内未发现优于基线的配置。';
export const NO_IMPROVEMENT_EN = 'No candidate improved the objective.';

export function systemOptimizationPath(id: string): string {
  return `/optimizations/system/${encodeURIComponent(id)}`;
}

export type CandidateKpiField = 'network_throughput_mbps' | 'average_ue_throughput_mbps' | 'p5_ue_throughput_mbps';

export interface SystemKpiMeta {
  id: string;
  field: CandidateKpiField;
  zh: string;
  en: string;
}

/** 目标 KPI 在前，其余为次要 KPI（全部由后端计算，前端只展示）。 */
export const SYSTEM_KPIS: SystemKpiMeta[] = [
  { id: NETWORK_THROUGHPUT, field: 'network_throughput_mbps', zh: '网络吞吐率', en: 'Network Throughput' },
  { id: AVG_UE_THROUGHPUT, field: 'average_ue_throughput_mbps', zh: '平均 UE 吞吐率', en: 'Average UE Throughput' },
  { id: P5_UE_THROUGHPUT, field: 'p5_ue_throughput_mbps', zh: 'P5 UE 吞吐率', en: 'P5 UE Throughput' },
];

export function kpiMeta(kpiId: string): SystemKpiMeta | undefined {
  return SYSTEM_KPIS.find((k) => k.id === kpiId);
}

export function stageLabel(stage: SystemOptimizationStage): { zh: string; en: string } {
  switch (stage) {
    case 'created':
      return { zh: '已创建', en: 'Created' };
    case 'preparing_context':
      return { zh: '准备公共评估上下文（光线追踪一次）', en: 'Preparing Common Evaluation Context' };
    case 'running_baseline':
      return { zh: '运行基线', en: 'Running Baseline' };
    case 'evaluating_candidate':
      return { zh: '评估候选', en: 'Evaluating Candidate' };
    case 'selecting_best':
      return { zh: '选择最优候选', en: 'Selecting Best Candidate' };
    case 'persisting_evidence':
      return { zh: '保存证据', en: 'Persisting Evidence' };
    case 'completed':
      return { zh: '已完成', en: 'Completed' };
    case 'failed':
      return { zh: '失败', en: 'Failed' };
    default: {
      const unreachable: never = stage;
      throw new Error(`Unknown optimization stage: ${String(unreachable)}`);
    }
  }
}

export const RUNNING_STAGES: SystemOptimizationStage[] = [
  'preparing_context',
  'running_baseline',
  'evaluating_candidate',
  'selecting_best',
  'persisting_evidence',
];

/** 真实计数（"Candidate 2/5"），不做百分比估计。 */
export function progressText(p: SystemOptimizationProgress): string {
  if (p.stage !== 'evaluating_candidate') return stageLabel(p.stage).en;
  const current = Math.min(p.completed_candidates + 1, p.total_candidates);
  const value = isNumber(p.current_parameter_value) ? ` (β = ${p.current_parameter_value})` : '';
  return `Candidate ${current}/${p.total_candidates}${value}`;
}

export function directionMeta(direction: KpiDirection): { symbol: string; zh: string; en: string; color: string } {
  switch (direction) {
    case 'increase':
      return { symbol: '↑', zh: '上升', en: 'Increase', color: 'success' };
    case 'decrease':
      return { symbol: '↓', zh: '下降', en: 'Decrease', color: 'error' };
    case 'unchanged':
      return { symbol: '→', zh: '不变', en: 'Unchanged', color: 'default' };
    default: {
      const unreachable: never = direction;
      throw new Error(`Unknown KPI direction: ${String(unreachable)}`);
    }
  }
}

export function formatMbps(v: number | null | undefined, digits = 2): string {
  return isNumber(v) ? `${v.toFixed(digits)} Mbps` : EMPTY;
}

export function formatPercentSigned(v: number | null | undefined, digits = 2): string {
  if (!isNumber(v)) return EMPTY;
  const sign = v > 0 ? '+' : v < 0 ? '−' : '±';
  return `${sign}${Math.abs(v).toFixed(digits)}%`;
}

export function formatParameter(v: number | null | undefined): string {
  return isNumber(v) ? String(Number(v.toFixed(6))) : EMPTY;
}

/** 允许的结论措辞（§ wording）；只引用后端给出的相对改善，不自行计算。 */
export function outcomeClaim(r: SystemOptimizationResponse): string | null {
  const c = r.comparison;
  if (!c) return null;
  if (!c.improved || !isNumber(c.relative_improvement_percent)) return NO_IMPROVEMENT_ZH;
  return `${ALLOWED_CLAIM_PREFIX}提高 ${c.relative_improvement_percent.toFixed(2)}%`;
}

export function allEvaluations(r: SystemOptimizationResponse): SystemOptimizationCandidate[] {
  return r.baseline ? [r.baseline, ...r.candidates] : [...r.candidates];
}

export function findCandidate(r: SystemOptimizationResponse, id: string | null | undefined) {
  return id ? allEvaluations(r).find((c) => c.candidate_id === id) : undefined;
}

export function candidateValue(c: SystemOptimizationCandidate, parameterId: string): number | undefined {
  return c.parameters[parameterId];
}

/** 表单输入校验：解析逗号分隔候选值并按参数定义的边界检查（不涉及 KPI 计算）。 */
export function validateCandidates(text: string, def: ParameterDefinition): { values: number[] } | { error: string } {
  const parts = text.split(/[\s,，]+/).filter((p) => p.length > 0);
  if (parts.length === 0) return { error: '至少需要一个候选值 / At least one candidate value' };
  const values = parts.map(Number);
  const bad = parts.filter((_, i) => !Number.isFinite(values[i]));
  if (bad.length) return { error: `非法数值 / Invalid number: ${bad.join(', ')}` };
  if (new Set(values).size !== values.length) return { error: '候选值重复 / Duplicate candidate values' };
  const b = def.bounds;
  if (b) {
    const out = values.filter(
      (v) => (b.lower_inclusive ? v < b.lower : v <= b.lower) || (b.upper_inclusive ? v > b.upper : v >= b.upper),
    );
    if (out.length) return { error: `超出范围 ${boundsText(def)} / Out of range: ${out.join(', ')}` };
  }
  return { values };
}

export function boundsText(def: ParameterDefinition): string {
  const b = def.bounds;
  if (!b) return EMPTY;
  return `${b.lower_inclusive ? '[' : '('}${b.lower}, ${b.upper}${b.upper_inclusive ? ']' : ')'}`;
}

/** 迭代算法（有 trace 且不是工程基线）显示 Algorithm Trace；Grid Search 保持 Candidate History。 */
export function isIterativeRun(r: SystemOptimizationResponse): boolean {
  return !!r.algorithm_trace && !!r.algorithm && r.algorithm.algorithm_category !== 'engineering_baseline';
}

export function parameterSpaceText(r: SystemOptimizationResponse): string {
  const def = r.parameter_space?.parameters.find((p) => p.id === r.parameter.id);
  if (!def) return r.candidate_values.join(', ');
  if (def.type === 'discrete') return `离散 Discrete {${(def.choices ?? []).join(', ')}}`;
  return `${def.type === 'continuous' ? '连续 Continuous' : def.type} ${boundsText(def)}`;
}
