import type { ExperimentPurpose } from '../types/experiment';
import type { ImprovementStatus, OptimizationCandidate } from '../types/optimization';
import { EMPTY, isNumber } from './format';

export const TX_POWER = 'tx_power_dbm';

export interface ImprovementMeta {
  zh: string;
  en: string;
  /** antd Tag / 文本语义色：只有真实改善才使用 success */
  color: 'success' | 'default' | 'warning';
}

export function improvementMeta(status: ImprovementStatus): ImprovementMeta {
  switch (status) {
    case 'improved':
      return { zh: '目标值改善', en: 'Objective Improved', color: 'success' };
    case 'no_improvement':
      return { zh: '未获得改善', en: 'No Improvement', color: 'default' };
    case 'worse':
      return { zh: '目标值下降', en: 'Objective Decreased', color: 'warning' };
    default: {
      const unreachable: never = status;
      throw new Error(`Unknown improvement status: ${String(unreachable)}`);
    }
  }
}

export function purposeMeta(purpose: ExperimentPurpose): { zh: string; en: string } | null {
  switch (purpose) {
    case 'manual':
      return null;
    case 'optimization_baseline':
      return { zh: '优化基线', en: 'Optimization Baseline' };
    case 'optimization_candidate':
      return { zh: '优化候选', en: 'Optimization Candidate' };
    default: {
      const unreachable: never = purpose;
      throw new Error(`Unknown experiment purpose: ${String(unreachable)}`);
    }
  }
}

const EVENT_LABELS: Record<string, { zh: string; en: string }> = {
  optimization_created: { zh: '优化实验创建', en: 'Optimization Created' },
  baseline_evaluated: { zh: '基线评价完成', en: 'Baseline Evaluated' },
  candidate_evaluated: { zh: '候选评价完成', en: 'Candidate Evaluated' },
  candidate_failed: { zh: '候选评价失败', en: 'Candidate Failed' },
  best_candidate_selected: { zh: '选定最优候选', en: 'Best Candidate Selected' },
  optimization_completed: { zh: '优化完成', en: 'Optimization Completed' },
  optimization_failed: { zh: '优化失败', en: 'Optimization Failed' },
};

export function eventLabel(event: string): { zh: string; en: string } {
  return EVENT_LABELS[event] ?? { zh: event, en: event };
}

export function formatObjective(v: number | null | undefined, digits = 4): string {
  return isNumber(v) ? v.toFixed(digits) : EMPTY;
}

export function formatSigned(v: number | null | undefined, digits = 4, suffix = ''): string {
  if (!isNumber(v)) return EMPTY;
  const sign = v > 0 ? '+' : v < 0 ? '−' : '±';
  return `${sign}${Math.abs(v).toFixed(digits)}${suffix}`;
}

export function formatPower(v: number | null | undefined): string {
  return isNumber(v) ? `${Number(v.toFixed(2))} dBm` : EMPTY;
}

export function candidatePower(c: OptimizationCandidate | null | undefined): number | undefined {
  return c?.parameters[TX_POWER];
}

export function component(c: OptimizationCandidate | null | undefined, key: string): number | undefined {
  return c?.objective?.components[key];
}

/** 从逗号/空格分隔的输入解析候选功率；非法项返回 null。 */
export function parseCandidateValues(text: string): number[] | null {
  const parts = text.split(/[\s,，]+/).filter((p) => p.length > 0);
  if (parts.length === 0) return null;
  const values = parts.map(Number);
  return values.every((v) => Number.isFinite(v)) ? values : null;
}
