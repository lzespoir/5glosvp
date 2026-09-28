import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { fixtureObjective, fixtureOptimization, fixtureOptimizer } from '../../test/optimizationFixtures';
import { renderWithProviders } from '../../test/render';
import { CreateOptimizationModal, validateCandidates } from './CreateOptimizationModal';

const GET_RESPONSES: Record<string, unknown> = {
  '/scenarios': { items: [{ scenario_id: 'SIONNA-DEMO-001', name_zh: '内置场景', name_en: 'Built-in Scene', backend: 'sionna_rt' }] },
  '/scenarios/SIONNA-DEMO-001': {
    scenario_id: 'SIONNA-DEMO-001',
    transmitters: [{ id: 'tx-0', position: [0, 0, 10], power_dbm: 44 }],
  },
  '/backends': {
    items: [{ id: 'sionna_rt', name_zh: 'Sionna RT 仿真后端', name_en: 'Sionna RT', available: true, version: '2.1.0', capabilities: [], reason: null, source_type: 'simulation' }],
  },
};

function mockGet() {
  return vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (!(url in GET_RESPONSES)) throw new Error(`unexpected GET ${url}`);
    return { data: GET_RESPONSES[url] } as AxiosResponse;
  });
}

function renderModal() {
  return renderWithProviders(
    <CreateOptimizationModal open optimizers={[fixtureOptimizer]} objectives={[fixtureObjective]} onClose={() => {}} />,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('CreateOptimizationModal', () => {
  it('prefills the backend-recommended demo search space and labels it as an assumption', async () => {
    mockGet();
    renderModal();
    expect((screen.getByLabelText('Candidate values') as HTMLInputElement).value).toBe('38, 40, 42, 44, 46');
    expect(screen.getByText(/演示搜索空间 Demo Search Space/)).toBeTruthy();
    expect(screen.getByText('发射功率 TX Power (dBm)')).toBeTruthy();
    expect(await screen.findByText(/44 dBm/)).toBeTruthy();
  });

  it('posts the parameter space and navigates to the optimization detail on success', async () => {
    mockGet();
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: fixtureOptimization(), status: 201 } as AxiosResponse);
    renderModal();
    const run = screen.getByRole('button', { name: /运行优化 Run Optimization/ });
    await vi.waitFor(() => expect(run.hasAttribute('disabled')).toBe(false));
    await userEvent.click(run);
    expect(await screen.findByTestId('optimization-route')).toBeTruthy();
    expect(post).toHaveBeenCalledWith(
      '/optimizations',
      expect.objectContaining({
        scenario_id: 'SIONNA-DEMO-001',
        optimizer_id: 'grid_search',
        objective_id: 'PROPAGATION_UTILITY_V0_1',
        parameter_space: { tx_power_dbm: [38, 40, 42, 44, 46] },
      }),
    );
  });

  it('treats HTTP 201 with status=failed as a failure and shows the failed candidate', async () => {
    mockGet();
    vi.spyOn(apiClient, 'post').mockResolvedValue({
      data: fixtureOptimization({
        status: 'failed',
        comparison: null,
        improvement_status: null,
        error: { code: 'OPTIMIZATION_FAILED', message: 'candidate exploded', type: 'RuntimeError', failed_candidate_id: 'CAND-002', experiment_id: null },
      }),
      status: 201,
    } as AxiosResponse);
    renderModal();
    const run = screen.getByRole('button', { name: /运行优化 Run Optimization/ });
    await vi.waitFor(() => expect(run.hasAttribute('disabled')).toBe(false));
    await userEvent.click(run);
    expect(await screen.findByText('优化实验失败 Optimization Failed')).toBeTruthy();
    expect(screen.getByText('OPTIMIZATION_FAILED')).toBeTruthy();
    expect(screen.getByText('CAND-002')).toBeTruthy();
    expect(screen.queryByTestId('optimization-route')).toBeNull();
  });

  it('validates candidate values', () => {
    expect(validateCandidates('38, 40', 10)).toBeNull();
    expect(validateCandidates('38, abc', 10)).toMatch(/数值/);
    expect(validateCandidates('38, 38', 10)).toMatch(/重复/);
    expect(validateCandidates('1,2,3,4,5,6,7,8,9,10,11', 10)).toMatch(/10/);
    expect(validateCandidates('', 10)).not.toBeNull();
  });
});
