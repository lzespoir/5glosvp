import type {
  AcceptanceIneligibilityReason,
  AlgorithmCategory,
  AlgorithmStatus,
  HyperparameterDefinition,
  HyperparameterValue,
  StopReason,
  VerificationStatus,
} from '../types/algorithm';
import type { ParameterType } from '../types/systemOptimization';

export const ALGORITHMS_PATH = '/algorithms';
export const INTEGRATION_GUIDE_PATH = '/algorithms/guide';
export const GRID_SEARCH_ID = 'grid_search';
/** 与后端 MAX_EVALUATION_BUDGET 一致；后端仍会校验（INVALID_EVALUATION_BUDGET）。 */
export const MAX_EVALUATION_BUDGET = 12;
export const DEFAULT_EVALUATION_BUDGET = 8;

export function algorithmPath(id: string): string {
  return `${ALGORITHMS_PATH}/${encodeURIComponent(id)}`;
}

export interface Label {
  zh: string;
  en: string;
  color: string;
}

export function categoryMeta(category: AlgorithmCategory): Label {
  switch (category) {
    case 'engineering_baseline':
      return { zh: '工程基线', en: 'Engineering Baseline', color: 'default' };
    case 'research_demo':
      return { zh: '接入验证算法', en: 'Integration Demo', color: 'purple' };
    case 'research':
      return { zh: '科研算法', en: 'Research Algorithm', color: 'blue' };
    case 'external':
      return { zh: '外部算法', en: 'External Algorithm', color: 'cyan' };
    default: {
      const unreachable: never = category;
      throw new Error(`Unknown algorithm category: ${String(unreachable)}`);
    }
  }
}

export function statusMeta(status: AlgorithmStatus): Label {
  switch (status) {
    case 'available':
      return { zh: '可用', en: 'Available', color: 'green' };
    case 'experimental':
      return { zh: '实验性', en: 'Experimental', color: 'orange' };
    case 'deprecated':
      return { zh: '已弃用', en: 'Deprecated', color: 'default' };
    default: {
      const unreachable: never = status;
      throw new Error(`Unknown algorithm status: ${String(unreachable)}`);
    }
  }
}

export function stopReasonMeta(reason: StopReason): Label {
  switch (reason) {
    case 'completed':
      return { zh: '完成（无更多建议）', en: 'Completed', color: 'green' };
    case 'max_iterations':
      return { zh: '达到最大迭代轮数', en: 'Max Iterations', color: 'blue' };
    case 'converged':
      return { zh: '收敛（步长低于下限）', en: 'Converged', color: 'green' };
    case 'no_improvement':
      return { zh: '无改善', en: 'No Improvement', color: 'default' };
    case 'budget_exhausted':
      return { zh: '评价预算用尽', en: 'Budget Exhausted', color: 'orange' };
    case 'failed':
      return { zh: '失败', en: 'Failed', color: 'error' };
    case 'cancelled':
      return { zh: '已取消', en: 'Cancelled', color: 'default' };
    default: {
      const unreachable: never = reason;
      throw new Error(`Unknown stop reason: ${String(unreachable)}`);
    }
  }
}

export function verificationMeta(status: VerificationStatus): Label {
  switch (status) {
    case 'not_verified':
      return { zh: '未复核', en: 'Not Verified', color: 'default' };
    case 'platform_checks_passed':
      return { zh: '平台检查通过', en: 'Platform Checks Passed', color: 'blue' };
    case 'platform_checks_failed':
      return { zh: '平台检查未通过', en: 'Platform Checks Failed', color: 'error' };
    case 'independently_verified':
      return { zh: '独立复核通过', en: 'Independently Verified', color: 'green' };
    case 'independent_verification_failed':
      return { zh: '独立复核未通过', en: 'Independent Verification Failed', color: 'error' };
    default: {
      const unreachable: never = status;
      throw new Error(`Unknown verification status: ${String(unreachable)}`);
    }
  }
}

export function acceptanceReasonLabel(reason: AcceptanceIneligibilityReason): string {
  switch (reason) {
    case 'simulation_only':
      return '仅仿真 Simulation only';
    case 'not_measured':
      return '非实测 Not measured';
    case 'not_huawei_data':
      return '非华为数据 Not Huawei data';
    case 'unconfirmed_acceptance_kpi':
      return '验收 KPI 未确认 Acceptance KPI unconfirmed';
    case 'engineering_baseline':
      return '工程基线算法 Engineering baseline';
    case 'integration_demo_algorithm':
      return '接入验证算法 Integration demo';
    case 'test_fixture':
      return '测试夹具 Test fixture';
    case 'not_succeeded':
      return '运行未成功 Not succeeded';
    default: {
      const unreachable: never = reason;
      throw new Error(`Unknown acceptance reason: ${String(unreachable)}`);
    }
  }
}

export function parameterTypeLabel(t: ParameterType): string {
  switch (t) {
    case 'continuous':
      return '连续 Continuous';
    case 'discrete':
      return '离散 Discrete';
    case 'integer':
      return '整数 Integer';
    case 'categorical':
      return '类别 Categorical';
    case 'vector':
      return '向量 Vector';
    default: {
      const unreachable: never = t;
      throw new Error(`Unknown parameter type: ${String(unreachable)}`);
    }
  }
}

export function formatHyperparameter(v: HyperparameterValue | undefined): string {
  if (v === undefined) return '—';
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  return String(v);
}

export function defaultHyperparameters(schema: HyperparameterDefinition[]): Record<string, HyperparameterValue> {
  return Object.fromEntries(schema.map((h) => [h.id, h.default]));
}

/** 表单即时提示；最终以后端 validate 结果为准。 */
export function hyperparameterError(h: HyperparameterDefinition, v: HyperparameterValue | undefined): string | null {
  if (v === undefined || v === null) return '必填 / Required';
  switch (h.type) {
    case 'boolean':
      return typeof v === 'boolean' ? null : '需要布尔值 / Boolean expected';
    case 'categorical':
      return (h.choices ?? []).includes(v) ? null : `可选 ${(h.choices ?? []).join(' / ')}`;
    case 'float':
    case 'integer': {
      if (typeof v !== 'number' || !Number.isFinite(v)) return '需要数值 / Number expected';
      if (h.type === 'integer' && !Number.isInteger(v)) return '需要整数 / Integer expected';
      const b = h.bounds;
      if (!b) return null;
      const low = b.lower_inclusive ? v < b.lower : v <= b.lower;
      const high = b.upper_inclusive ? v > b.upper : v >= b.upper;
      return low || high
        ? `范围 ${b.lower_inclusive ? '[' : '('}${b.lower}, ${b.upper}${b.upper_inclusive ? ']' : ')'}`
        : null;
    }
    default: {
      const unreachable: never = h.type;
      throw new Error(`Unknown hyperparameter type: ${String(unreachable)}`);
    }
  }
}

/** 算法当前能端到端编辑的参数类型（Day 7：continuous 优先，其次 discrete）。 */
export function editableParameterType(supported: ParameterType[]): 'continuous' | 'discrete' | null {
  if (supported.includes('continuous')) return 'continuous';
  if (supported.includes('discrete')) return 'discrete';
  return null;
}

export function shortHash(h: string | null | undefined, n = 12): string {
  return h ? `${h.slice(0, n)}…` : '—';
}
