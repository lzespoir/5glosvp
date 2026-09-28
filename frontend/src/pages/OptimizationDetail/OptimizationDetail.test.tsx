import { screen, within } from '@testing-library/react';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { succeededExperiment } from '../../test/fixtures';
import { fixtureOptimization } from '../../test/optimizationFixtures';
import { renderWithProviders } from '../../test/render';
import type { OptimizationResponse } from '../../types/optimization';
import { OptimizationDetailPage, SCIENTIFIC_NOTE } from './index';

vi.mock('../../components/ObjectiveHistoryChart', () => ({
  ObjectiveHistoryChart: () => <div data-testid="history-chart" />,
}));

function mockGet(opt: OptimizationResponse) {
  return vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === `/optimizations/${opt.optimization_id}`) return { data: opt } as AxiosResponse;
    const match = /^\/experiments\/(EXP-[0-9A-Z]+)$/.exec(url);
    if (match) return { data: succeededExperiment({ experiment_id: match[1] }) } as AxiosResponse;
    throw new Error(`unexpected GET ${url}`);
  });
}

function renderDetail(opt: OptimizationResponse) {
  mockGet(opt);
  return renderWithProviders(<OptimizationDetailPage />, {
    path: '/optimizations/:optimizationId',
    route: `/optimizations/${opt.optimization_id}`,
  });
}

afterEach(() => vi.restoreAllMocks());

describe('OptimizationDetailPage', () => {
  it('renders before/after, the candidate table with BASELINE and reused rows, and experiment links', async () => {
    renderDetail(fixtureOptimization());
    expect(await screen.findByText('OPT-AAAA0001')).toBeTruthy();
    expect(screen.getByText('优化前')).toBeTruthy();
    expect(screen.getByText('优化后')).toBeTruthy();
    expect(screen.getByText('BASELINE 基线')).toBeTruthy();
    expect(screen.getByText('Reused Baseline 复用基线结果')).toBeTruthy();
    expect(screen.getByTestId('experiment-link-CAND-002').getAttribute('href')).toBe('/experiments/EXP-CAND0002');
    expect(screen.getByTestId('history-chart')).toBeTruthy();
    await vi.waitFor(() => expect(screen.getAllByAltText(/Radio map of EXP-/)).toHaveLength(2));
    expect(screen.getByAltText('Radio map of EXP-BASE0001')).toBeTruthy();
    expect(screen.getByAltText('Radio map of EXP-CAND0001')).toBeTruthy();
  });

  it('labels the objective as Objective Improvement, never acceptance KPI, and shows the scientific note', async () => {
    renderDetail(fixtureOptimization());
    expect(await screen.findByText('优化目标改善')).toBeTruthy();
    expect(screen.queryByText(/Acceptance KPI/)).toBeNull();
    expect(screen.queryByText(/Optimization Speed/)).toBeNull();
    expect(screen.getByText(SCIENTIFIC_NOTE)).toBeTruthy();
    expect(within(screen.getByTestId('improvement-status')).getByText(/Objective Improved/)).toBeTruthy();
  });

  it('marks λ and τ as assumptions in the breakdown', async () => {
    renderDetail(fixtureOptimization());
    await screen.findByText('目标函数分解');
    expect(screen.getAllByText('[A] Assumption').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('J = C_sinr - λ·c_P')).toBeTruthy();
  });

  it('shows No Improvement neutrally when the baseline stays best', async () => {
    const base = fixtureOptimization();
    const value = base.comparison?.baseline_objective ?? 0;
    renderDetail(
      fixtureOptimization({
        improvement_status: 'no_improvement',
        comparison: {
          ...(base.comparison as NonNullable<OptimizationResponse['comparison']>),
          optimized_objective: value,
          absolute_improvement: 0,
          relative_improvement_percent: 0,
        },
      }),
    );
    expect(await screen.findByText(/未获得改善 No Improvement/)).toBeTruthy();
    expect(screen.getByTestId('absolute-improvement').textContent).toContain('±0.0000');
  });

  it('shows relative improvement as unavailable when the backend returns null', async () => {
    const base = fixtureOptimization();
    renderDetail(
      fixtureOptimization({
        improvement_status: 'worse',
        comparison: {
          ...(base.comparison as NonNullable<OptimizationResponse['comparison']>),
          absolute_improvement: -0.01,
          relative_improvement_percent: null,
        },
      }),
    );
    expect(await screen.findByText(/目标值下降 Objective Decreased/)).toBeTruthy();
    expect(screen.getByTestId('absolute-improvement').textContent).toContain('−0.0100');
    expect(screen.getByTestId('relative-improvement').textContent).toMatch(/不可用/);
  });

  it('shows the failure and keeps the candidate table for failed runs', async () => {
    renderDetail(
      fixtureOptimization({
        status: 'failed',
        comparison: null,
        improvement_status: null,
        best_candidate: null,
        error: { code: 'OPTIMIZATION_FAILED', message: 'candidate exploded', type: 'RuntimeError', failed_candidate_id: 'CAND-002', experiment_id: null },
      }),
    );
    expect(await screen.findByText('优化实验失败 Optimization Failed')).toBeTruthy();
    expect(screen.queryByText('优化前')).toBeNull();
    expect(screen.getByText('BASELINE 基线')).toBeTruthy();
  });
});
