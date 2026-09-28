import { fireEvent, screen } from '@testing-library/react';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { renderWithProviders } from '../../test/render';
import { fixtureSystemBackend, fixtureSystemExperiment, fixtureSystemScenario } from '../../test/systemFixtures';
import type { SystemBackendView } from '../../types/system';
import { SystemPage } from './index';

vi.mock('../../components/NetworkView', () => ({ NetworkView: () => <div data-testid="network-view" /> }));

function mockApi(backend: SystemBackendView) {
  const detail = fixtureSystemScenario();
  const { scenario: _scenario, ...summary } = detail;
  vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === '/system-backends') return { data: { items: [backend] } } as AxiosResponse;
    if (url === '/system-scenarios') return { data: { items: [summary] } } as AxiosResponse;
    if (url === `/system-scenarios/${detail.scenario_id}`) return { data: detail } as AxiosResponse;
    if (url === '/system-experiments') {
      return { data: { items: [fixtureSystemExperiment()], total: 1, limit: 10, offset: 0 } } as AxiosResponse;
    }
    throw new Error(`unexpected GET ${url}`);
  });
}

afterEach(() => vi.restoreAllMocks());

describe('SystemPage', () => {
  it('shows scenario parameters, boundary and recent experiments', async () => {
    mockApi(fixtureSystemBackend());
    renderWithProviders(<SystemPage />, { path: '/system', route: '/system' });
    expect(await screen.findByText('3.5 GHz')).toBeTruthy();
    expect(screen.getByText('100 MHz')).toBeTruthy();
    expect(screen.getByTestId('scientific-boundary')).toBeTruthy();
    expect(screen.getByText(/满缓冲 Full Buffer/)).toBeTruthy();
    expect(await screen.findByTestId('network-view')).toBeTruthy();
    expect(await screen.findByText('EXP-5Y5TEM01')).toBeTruthy();
    expect(screen.getByText('70.00 Mbps')).toBeTruthy();
  });

  it('opens the run modal and disables running when the backend is unavailable', async () => {
    mockApi(fixtureSystemBackend({ available: false, reason: 'torch missing' }));
    renderWithProviders(<SystemPage />, { path: '/system', route: '/system' });
    const button = await screen.findByTestId('run-system');
    expect(button.hasAttribute('disabled')).toBe(true);
  });

  it('runs a system experiment and navigates to the result page', async () => {
    mockApi(fixtureSystemBackend());
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: fixtureSystemExperiment() } as AxiosResponse);
    renderWithProviders(<SystemPage />, { path: '/system', route: '/system' });
    fireEvent.click(await screen.findByTestId('run-system'));
    fireEvent.click(await screen.findByText('开始运行'));
    await vi.waitFor(() => expect(post).toHaveBeenCalled());
    expect(post.mock.calls[0]?.[0]).toBe('/system-experiments');
    expect(post.mock.calls[0]?.[1]).toMatchObject({ scenario_id: 'SYSTEM-DEMO-001', backend_id: 'sionna_system' });
  });
});
