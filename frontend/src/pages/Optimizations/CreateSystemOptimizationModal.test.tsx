import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { algorithmList, compatible, demoDetail, gridDetail } from '../../test/algorithmFixtures';
import { renderWithProviders } from '../../test/render';
import { fixtureSystemBackend, fixtureSystemScenario } from '../../test/systemFixtures';
import {
  fixtureObjective,
  fixtureParameter,
  fixtureProtocol,
  fixtureSystemOptimization,
} from '../../test/systemOptimizationFixtures';
import type { AlgorithmValidateRequest, CompatibilityReport } from '../../types/algorithm';
import { CreateSystemOptimizationModal } from './CreateSystemOptimizationModal';

type Validate = (id: string, body: AlgorithmValidateRequest) => CompatibilityReport;

function mockApi(validate: Validate = (id) => compatible(id)) {
  const detail = fixtureSystemScenario();
  const { scenario: _scenario, ...summary } = detail;
  vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === '/system-backends') {
      return { data: { items: [fixtureSystemBackend({ capabilities: ['system_simulation', 'channel_reuse'] })] } } as AxiosResponse;
    }
    if (url === '/system-scenarios') return { data: { items: [summary] } } as AxiosResponse;
    if (url === `/system-scenarios/${detail.scenario_id}`) return { data: detail } as AxiosResponse;
    if (url === '/algorithms/grid_search') return { data: gridDetail } as AxiosResponse;
    if (url === '/algorithms/research_demo_optimizer') return { data: demoDetail } as AxiosResponse;
    throw new Error(`unexpected GET ${url}`);
  });
  const create = vi.fn();
  vi.spyOn(apiClient, 'post').mockImplementation(async (url: string, body: unknown) => {
    const m = /^\/algorithms\/([^/]+)\/validate$/.exec(url);
    if (m?.[1]) return { data: validate(m[1], body as AlgorithmValidateRequest) } as AxiosResponse;
    if (url === '/system-optimizations') {
      create(body);
      return { data: fixtureSystemOptimization({ status: 'running' }) } as AxiosResponse;
    }
    throw new Error(`unexpected POST ${url}`);
  });
  return create;
}

function renderModal() {
  return renderWithProviders(
    <CreateSystemOptimizationModal
      open
      algorithms={algorithmList.items}
      objectives={[fixtureObjective]}
      parameters={[fixtureParameter]}
      protocols={[fixtureProtocol()]}
      onClose={() => undefined}
    />,
    { path: '/optimizations', route: '/optimizations' },
  );
}

async function chooseAlgorithm(label: RegExp) {
  fireEvent.mouseDown(screen.getByLabelText('Algorithm'));
  fireEvent.click(await screen.findByText(label, { selector: '.ant-select-item-option-content' }));
}

async function waitRunnable() {
  const run = await screen.findByRole('button', { name: /Start Optimization/ });
  await waitFor(() => expect(run.hasAttribute('disabled')).toBe(false), { timeout: 3000 });
  return run;
}

afterEach(() => vi.restoreAllMocks());

describe('CreateSystemOptimizationModal', () => {
  it('Grid Search: discrete candidates from the registry, compatibility checked, posts parameter_space', async () => {
    const create = mockApi();
    renderModal();
    const input = screen.getByLabelText('Candidate values') as HTMLInputElement;
    expect(input.value).toBe('0.1, 0.3, 0.6, 0.9, 0.99');
    fireEvent.click(await waitRunnable());
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create).toHaveBeenCalledWith(expect.objectContaining({
      problem_type: 'system',
      algorithm_id: 'grid_search',
      objective_id: 'NETWORK_THROUGHPUT_MAX_V0_1',
      parameter_space: { parameters: [{ id: 'scheduler_beta', type: 'discrete', choices: [0.1, 0.3, 0.6, 0.9, 0.99] }] },
      algorithm_hyperparameters: {},
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

  it('Research Demo: continuous editor with recommended bounds, Recommended settings, no budget override', async () => {
    const create = mockApi();
    renderModal();
    await chooseAlgorithm(/Research Demo Optimizer（自适应局部搜索）/);
    expect(await screen.findByTestId('continuous-editor')).toBeTruthy();
    expect((screen.getByLabelText('Lower bound') as HTMLInputElement).value).toBe('0.05');
    expect((screen.getByLabelText('Upper bound') as HTMLInputElement).value).toBe('0.99');
    expect(screen.getByText(/不是项目科研成果/)).toBeTruthy();
    const settings = screen.getByTestId('algorithm-settings');
    expect(await within(settings).findByText('0.2')).toBeTruthy();
    expect(await screen.findByText('兼容 Compatible')).toBeTruthy();
    fireEvent.click(await waitRunnable());
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create).toHaveBeenCalledWith(expect.objectContaining({
      algorithm_id: 'research_demo_optimizer',
      parameter_space: { parameters: [{ id: 'scheduler_beta', type: 'continuous', lower: 0.05, upper: 0.99 }] },
      algorithm_hyperparameters: {},
    }));
    expect(create.mock.calls[0]?.[0].evaluation_budget).toBeUndefined();
  });

  it('Advanced settings send hyperparameters and the evaluation budget', async () => {
    const create = mockApi();
    renderModal();
    await chooseAlgorithm(/Research Demo Optimizer（自适应局部搜索）/);
    fireEvent.click(await screen.findByText('高级 Advanced'));
    fireEvent.change(await screen.findByLabelText('initial_step'), { target: { value: '0.1' } });
    fireEvent.change(screen.getByLabelText('Evaluation budget'), { target: { value: '4' } });
    fireEvent.click(await waitRunnable());
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create).toHaveBeenCalledWith(expect.objectContaining({
      algorithm_hyperparameters: { initial_step: 0.1, max_iterations: 8, start_point: 'baseline' },
      evaluation_budget: { max_evaluations: 4 },
    }));
  });

  it('shows compatibility errors from the backend and blocks running', async () => {
    mockApi((id) => ({
      algorithm_id: id, compatible: false, warnings: [], resolved_hyperparameters: null,
      errors: [{ code: 'INVALID_HYPERPARAMETER', message: 'min_step must be <= initial_step', parameter_id: null }],
    }));
    renderModal();
    expect(await screen.findByText('算法与问题不兼容 Incompatible')).toBeTruthy();
    expect(screen.getByText('INVALID_HYPERPARAMETER')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Start Optimization/ }).hasAttribute('disabled')).toBe(true);
  });

  it('rejects widening the recommended continuous interval', async () => {
    mockApi();
    renderModal();
    await chooseAlgorithm(/Research Demo Optimizer（自适应局部搜索）/);
    fireEvent.change(await screen.findByLabelText('Upper bound'), { target: { value: '1.2' } });
    fireEvent.blur(screen.getByLabelText('Upper bound'));
    expect(await screen.findByText(/只能收窄推荐区间/)).toBeTruthy();
  });
});
