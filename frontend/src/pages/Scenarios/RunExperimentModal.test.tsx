import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { failedExperiment, succeededExperiment } from '../../test/fixtures';
import { renderWithProviders } from '../../test/render';
import type { BackendInfo } from '../../types/backend';
import type { ScenarioSummary } from '../../types/scenario';
import { RunExperimentModal } from './RunExperimentModal';

const scenario: ScenarioSummary = {
  scenario_id: 'SIONNA-DEMO-001',
  name_zh: '内置场景',
  name_en: 'Built-in Scene',
  backend: 'sionna_rt',
};

const backend: BackendInfo = {
  id: 'sionna_rt',
  name_zh: 'Sionna RT 仿真后端',
  name_en: 'Sionna RT',
  available: true,
  version: '2.1.0',
  capabilities: ['radio_map'],
  reason: null,
  source_type: 'simulation',
};

function mockPost(data: unknown) {
  return vi.spyOn(apiClient, 'post').mockResolvedValue({ data, status: 201 } as AxiosResponse);
}

afterEach(() => vi.restoreAllMocks());

describe('RunExperimentModal', () => {
  it('shows confirmation details with simulation data type', () => {
    renderWithProviders(<RunExperimentModal open scenario={scenario} backend={backend} onClose={() => {}} />);
    expect(screen.getByText('SIONNA-DEMO-001')).toBeTruthy();
    expect(screen.getByText(/仿真生成 \/ Simulation Generated/)).toBeTruthy();
    expect(screen.getByRole('button', { name: '开始运行' })).toBeTruthy();
  });

  it('treats HTTP 201 with status=failed as a failure', async () => {
    const post = mockPost(failedExperiment());
    renderWithProviders(<RunExperimentModal open scenario={scenario} backend={backend} onClose={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: '开始运行' }));

    expect(await screen.findByText('实验执行失败 Experiment Failed')).toBeTruthy();
    expect(screen.getByText('SIMULATION_FAILED')).toBeTruthy();
    expect(screen.getByText('ray tracer exploded')).toBeTruthy();
    expect(screen.queryByTestId('detail-route')).toBeNull();
    expect(post).toHaveBeenCalledWith('/experiments', expect.objectContaining({ scenario_id: 'SIONNA-DEMO-001' }));
    const body = post.mock.calls[0]?.[1] as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual(['name', 'scenario_id']);
  });

  it('navigates to the detail page on success', async () => {
    mockPost(succeededExperiment());
    renderWithProviders(<RunExperimentModal open scenario={scenario} backend={backend} onClose={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: '开始运行' }));
    expect(await screen.findByTestId('detail-route')).toBeTruthy();
  });

  it('disables running when the backend is unavailable', () => {
    renderWithProviders(
      <RunExperimentModal
        open
        scenario={scenario}
        backend={{ ...backend, available: false, reason: 'GPU missing' }}
        onClose={() => {}}
      />,
    );
    expect(screen.getByRole('button', { name: '开始运行' }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByText('GPU missing')).toBeTruthy();
  });

  it('labels fake backend data as TEST FIXTURE', () => {
    renderWithProviders(
      <RunExperimentModal
        open
        scenario={{ ...scenario, backend: 'fake' }}
        backend={{ ...backend, id: 'fake', source_type: 'test_fixture' }}
        onClose={() => {}}
      />,
    );
    expect(screen.getByText(/测试数据 \/ TEST FIXTURE/)).toBeTruthy();
    expect(screen.queryByText(/Simulation Generated/)).toBeNull();
  });
});
