import {
  eventLabel,
  formatSigned,
  improvementMeta,
  parseCandidateValues,
  purposeMeta,
} from './optimization';

describe('optimization utils', () => {
  it('colors only real improvement as success', () => {
    expect(improvementMeta('improved').color).toBe('success');
    expect(improvementMeta('no_improvement')).toMatchObject({ zh: '未获得改善', en: 'No Improvement', color: 'default' });
    expect(improvementMeta('worse').color).toBe('warning');
  });

  it('formats signed values including zero', () => {
    expect(formatSigned(0.01234)).toBe('+0.0123');
    expect(formatSigned(-0.5, 2, '%')).toBe('−0.50%');
    expect(formatSigned(0)).toBe('±0.0000');
    expect(formatSigned(null)).toBe('—');
  });

  it('parses comma separated candidates', () => {
    expect(parseCandidateValues('38, 40，42 44')).toEqual([38, 40, 42, 44]);
    expect(parseCandidateValues('38, x')).toBeNull();
    expect(parseCandidateValues('  ')).toBeNull();
  });

  it('labels experiment purpose and events', () => {
    expect(purposeMeta('manual')).toBeNull();
    expect(purposeMeta('optimization_baseline')?.en).toBe('Optimization Baseline');
    expect(eventLabel('best_candidate_selected').zh).toBe('选定最优候选');
    expect(eventLabel('something_new').en).toBe('something_new');
  });
});
