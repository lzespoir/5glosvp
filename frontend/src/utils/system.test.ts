import { fixtureSystemExperiment } from '../test/systemFixtures';
import { findKpi, modelMeta, NETWORK_THROUGHPUT, unavailableReason } from './system';

describe('system utils', () => {
  it('labels each model type distinctly', () => {
    expect(modelMeta('sionna_sys').label).toBe('Sionna Simulation Generated');
    expect(modelMeta('engineering_approximation').label).toBe('Fast Engineering Approximation');
    expect(modelMeta('test_fixture').label).toBe('TEST FIXTURE');
    expect(modelMeta(null).label).toBe('Unknown Source');
    const classes = new Set(['sionna_sys', 'engineering_approximation', 'test_fixture'].map((t) => modelMeta(t as never).className));
    expect(classes.size).toBe(3);
  });

  it('finds KPIs by id without computing anything', () => {
    const exp = fixtureSystemExperiment();
    expect(findKpi(exp.kpis, NETWORK_THROUGHPUT)?.value).toBe(70);
    expect(findKpi(exp.kpis, 'UNKNOWN')).toBeUndefined();
  });

  it('returns the backend reason for missing UE fields', () => {
    const ue = fixtureSystemExperiment().result?.ue_results[2];
    expect(ue && unavailableReason(ue, 'sinr_eff_db_mean')).toMatch(/never scheduled/);
    expect(ue && unavailableReason(ue, 'tx_power_w_mean')).toMatch(/Not returned/);
  });
});
