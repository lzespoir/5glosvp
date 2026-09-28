import { fireEvent, screen, waitFor } from '@testing-library/react';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { renderWithProviders } from '../../test/render';
import { fixtureSystemBackend, fixtureSystemScenario } from '../../test/systemFixtures';
import {
  fixtureObjective,
  fixtureOptimizer,
  fixtureParameter,
  fixtureProtocol,
  fixtureSystemOptimization,
} from '../../test/systemOptimizationFixtures';
import { CreateSystemOptimizationModal } from './CreateSystemOptimizationModal';

function mockApi() {
  const detail = fixtureSystemScenario();
  const { scenario: _scenario, ...summary } = detail;
  vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === '/system-backends') {
      return { data: { items: [fixtureSystemBackend({ capabilities: ['system_simulation', 'channel_reuse'] })] } } as AxiosResponse;
    }
    if (url === '/system-scenarios') return { data: { items: [summary] } } as AxiosResponse;
    if (url === `/system-scenarios/${detail.scenario_id}`) return { data: detail } as AxiosResponse;
    throw new Error(`unexpected GET ${url}`);
  });
}

function renderModal() {
  return renderWithProviders(
    <CreateSystemOptimizationModal
      open
      optimizers={[fixtureOptimizer]}
      objectives={[fixtureObjective]}
      parameters={[fixtureParameter]}
      protocols={[fixtureProtocol()]}
      onClose={() => undefined}
    />,
    { path: '/optimizations', route: '/optimizations' },
  );
}

afterEach(() => vi.restoreAllMocks());

describe('CreateSystemOptimizationModal', () => {
  it('prefills recommended β values, posts a system problem and navigates to the detail page', async () => {
    mockApi();
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: fixtureSystemOptimization({ status: 'running' }) } as AxiosResponse);
    renderModal();
    const input = screen.getByLabelText('Candidate values') as HTMLInputElement;
    expect(input.value).toBe('0.1, 0.3, 0.6, 0.9, 0.99');
    const run = await screen.findByRole('button', { name: /Start Optimization/ });
    await waitFor(() => expect(run.hasAttribute('disabled')).toBe(false));
    fireEvent.click(run);
    await waitFor(() => expect(post).toHaveBeenCalled());
    expect(post).toHaveBeenCalledWith('/system-optimizations', expect.objectContaining({
      problem_type: 'system',
      optimizer_id: 'grid_search',
      objective_id: 'NETWORK_THROUGHPUT_MAX_V0_1',
      parameter: { id: 'scheduler_beta', candidate_values: [0.1, 0.3, 0.6, 0.9, 0.99] },
      benchmark_protocol_id: 'SYSTEM_BENCHMARK_V0_1',
    }));
    expect(await screen.findByTestId('system-optimization-route')).toBeTruthy();
  });

  it('rejects β = 0 (outside the open interval) and disables running', async () => {
    mockApi();
    renderModal();
    fireEvent.change(screen.getByLabelText('Candidate values'), { target: { value: '0.0, 0.5' } });
    expect(await screen.findByText(/超出范围/)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Start Optimization/ }).hasAttribute('disabled')).toBe(true);
  });

  it('keeps algorithm settings separate from the optimization variable', async () => {
    mockApi();
    renderModal();
    fireEvent.click(screen.getByText('高级设置 Advanced Settings'));
    expect(await screen.findByText('算法设置 Algorithm Settings')).toBeTruthy();
    expect(screen.getByText(/Grid Search 无算法超参数/)).toBeTruthy();
  });
});
