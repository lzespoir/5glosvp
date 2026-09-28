import { fireEvent, screen, within } from '@testing-library/react';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { renderWithProviders } from '../../test/render';
import { fixtureSystemOptimization, OPT_ID } from '../../test/systemOptimizationFixtures';
import type { SystemOptimizationResponse } from '../../types/systemOptimization';
import { SystemOptimizationDetailPage } from './index';

vi.mock('./CandidateHistoryChart', () => ({ CandidateHistoryChart: () => <div data-testid="history-chart" /> }));
vi.mock('./PerUeComparison', () => ({ PerUeComparison: () => <div data-testid="per-ue" /> }));

const FORBIDDEN = ['5G 网络性能提升', '项目指标提升', '现网提升'];

function renderDetail(o: SystemOptimizationResponse) {
  vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === `/system-optimizations/${o.optimization_id}`) return { data: o } as AxiosResponse;
    throw new Error(`unexpected GET ${url}`);
  });
  return renderWithProviders(<SystemOptimizationDetailPage />, { path: '/opt/:optimizationId', route: `/opt/${o.optimization_id}` });
}

afterEach(() => vi.restoreAllMocks());

describe('SystemOptimizationDetailPage', () => {
  it('shows baseline vs best, the allowed claim and scientific boundary', async () => {
    const { container } = renderDetail(fixtureSystemOptimization());
    const hero = await screen.findByTestId('hero-comparison');
    expect(within(hero).getByText('BASELINE')).toBeTruthy();
    expect(within(hero).getByText('BEST CANDIDATE')).toBeTruthy();
    expect(within(hero).getByTestId('hero-delta').textContent).toContain('+80.23%');
    expect(screen.getByText('在当前冻结仿真协议下，网络吞吐率提高 80.23%')).toBeTruthy();
    expect(screen.getByText('当前结果来自系统级仿真优化验证，不是华为实测网络优化结果。')).toBeTruthy();
    expect(screen.getByText('Grid Search 为工程基线优化器，不属于项目学习优化算法。')).toBeTruthy();
    for (const phrase of FORBIDDEN) expect(container.textContent).not.toContain(phrase);
  });

  it('keeps the negative P5 trade-off visible', async () => {
    renderDetail(fixtureSystemOptimization());
    const p5 = await screen.findByTestId('kpi-direction-P5_UE_THROUGHPUT_V0_1');
    expect(p5.textContent).toContain('↓');
    expect(p5.textContent).toContain('−17.94%');
    expect(screen.getByText('存在负向 trade-off / Negative trade-off')).toBeTruthy();
  });

  it('lists every candidate including the failed one, with experiment links back to this optimization', async () => {
    renderDetail(fixtureSystemOptimization());
    const table = await screen.findByTestId('candidate-table');
    expect(within(table).getByText('CAND-003')).toBeTruthy();
    expect(within(table).getByText('failed')).toBeTruthy();
    expect(within(table).getByText('Best')).toBeTruthy();
    fireEvent.click(within(table).getByText('EXP-CAND002'));
    expect(await screen.findByTestId('system-experiment-route')).toBeTruthy();
  });

  it('shows the evaluation protocol with fairness badges', async () => {
    renderDetail(fixtureSystemOptimization());
    expect(await screen.findByText('Fair Evaluation Conditions')).toBeTruthy();
    expect(screen.getByTestId('fairness-same_channel_realization').textContent).toContain('Same Channel Realization');
    expect(screen.getByText('500 slots · warm-up 0')).toBeTruthy();
  });

  it('shows the no-improvement text instead of a claim', async () => {
    const base = fixtureSystemOptimization();
    const comparison = base.comparison ? { ...base.comparison, improved: false, absolute_improvement: 0, relative_improvement_percent: 0 } : null;
    const { container } = renderDetail({ ...base, comparison });
    expect(await screen.findByTestId('no-improvement')).toBeTruthy();
    expect(screen.getByText('当前候选范围内未发现优于基线的配置。')).toBeTruthy();
    expect(container.textContent).not.toContain('网络吞吐率提高');
  });

  it('shows real running stages with a candidate counter and no percentage', async () => {
    renderDetail(
      fixtureSystemOptimization({
        status: 'running',
        comparison: null,
        best_candidate_id: null,
        progress: { stage: 'evaluating_candidate', completed_candidates: 1, total_candidates: 5, current_candidate_id: 'CAND-002', current_parameter_value: 0.3 },
      }),
    );
    const progress = await screen.findByTestId('progress-text');
    expect(progress.textContent).toContain('Candidate 2/5');
    expect(progress.textContent).not.toMatch(/\d+%/);
    expect(screen.getByTestId('running-stages')).toBeTruthy();
  });

  it('shows backend warnings verbatim', async () => {
    renderDetail(fixtureSystemOptimization({ warnings: ['Improvement is within observed simulation variability.'] }));
    expect(await screen.findByText('Improvement is within observed simulation variability.')).toBeTruthy();
  });

  it('shows the optimization id and protocol in the header', async () => {
    renderDetail(fixtureSystemOptimization());
    expect(await screen.findByText(OPT_ID)).toBeTruthy();
    expect(screen.getAllByText(/SYSTEM_BENCHMARK_V0_1 v0.1/).length).toBeGreaterThan(0);
  });
});
