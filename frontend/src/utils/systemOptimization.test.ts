import { betaDefinition, fixtureSystemOptimization } from '../test/systemOptimizationFixtures';
import type { SystemOptimizationStage } from '../types/systemOptimization';
import {
  directionMeta,
  formatPercentSigned,
  NO_IMPROVEMENT_ZH,
  outcomeClaim,
  progressText,
  stageLabel,
  systemOptimizationPath,
  validateCandidates,
} from './systemOptimization';

describe('system optimization utils', () => {
  it('reports real candidate counts, never percentages', () => {
    const text = progressText({
      stage: 'evaluating_candidate', completed_candidates: 1, total_candidates: 5, current_candidate_id: 'CAND-002', current_parameter_value: 0.3,
    });
    expect(text).toBe('Candidate 2/5 (β = 0.3)');
    expect(progressText({ stage: 'running_baseline', completed_candidates: 0, total_candidates: 5, current_candidate_id: null, current_parameter_value: null }))
      .toBe('Running Baseline');
  });

  it('labels every stage', () => {
    const stages: SystemOptimizationStage[] = [
      'created', 'preparing_context', 'running_baseline', 'evaluating_candidate', 'selecting_best', 'persisting_evidence', 'completed', 'failed',
    ];
    for (const s of stages) expect(stageLabel(s).en.length).toBeGreaterThan(0);
  });

  it('validates candidates against the open (0, 1) interval', () => {
    expect(validateCandidates('0.1, 0.3, 0.99', betaDefinition)).toEqual({ values: [0.1, 0.3, 0.99] });
    expect('error' in validateCandidates('0.0, 0.5', betaDefinition)).toBe(true);
    expect('error' in validateCandidates('1', betaDefinition)).toBe(true);
    expect('error' in validateCandidates('0.5, 0.5', betaDefinition)).toBe(true);
    expect('error' in validateCandidates('abc', betaDefinition)).toBe(true);
    expect('error' in validateCandidates('', betaDefinition)).toBe(true);
  });

  it('uses only the allowed claim wording, quoting the backend value', () => {
    expect(outcomeClaim(fixtureSystemOptimization())).toBe('在当前冻结仿真协议下，网络吞吐率提高 80.23%');
    const base = fixtureSystemOptimization();
    const flat = base.comparison ? { ...base.comparison, improved: false } : null;
    expect(outcomeClaim({ ...base, comparison: flat })).toBe(NO_IMPROVEMENT_ZH);
    expect(outcomeClaim({ ...base, comparison: null })).toBeNull();
  });

  it('formats directions and signed percentages', () => {
    expect(directionMeta('decrease').symbol).toBe('↓');
    expect(formatPercentSigned(-17.94)).toBe('−17.94%');
    expect(formatPercentSigned(null)).toBe('—');
    expect(systemOptimizationPath('OPT-1')).toBe('/optimizations/system/OPT-1');
  });
});
