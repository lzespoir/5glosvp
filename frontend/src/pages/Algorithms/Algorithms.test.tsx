import { fireEvent, screen, within } from '@testing-library/react';
import type { AxiosResponse } from 'axios';
import { Route, Routes } from 'react-router-dom';

import { apiClient } from '../../api/client';
import { algorithmList, demoDetail, evidenceDescriptor } from '../../test/algorithmFixtures';
import { renderWithProviders } from '../../test/render';
import { AcceptancePage } from '../Acceptance';
import { AlgorithmDetailPage } from './AlgorithmDetail';
import { AlgorithmsPage } from './index';
import { IntegrationGuidePage } from './IntegrationGuide';

function mockApi() {
  vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === '/algorithms') return { data: algorithmList } as AxiosResponse;
    if (url === '/algorithms/research_demo_optimizer') return { data: demoDetail } as AxiosResponse;
    if (url === '/evidence') return { data: { items: [evidenceDescriptor], total: 1 } } as AxiosResponse;
    throw new Error(`unexpected GET ${url}`);
  });
}

function AlgorithmRoutes() {
  return (
    <Routes>
      <Route index element={<AlgorithmsPage />} />
      <Route path="guide" element={<IntegrationGuidePage />} />
      <Route path=":algorithmId" element={<AlgorithmDetailPage />} />
    </Routes>
  );
}

afterEach(() => vi.restoreAllMocks());

describe('Algorithm Center', () => {
  it('lists registry algorithms with honest labels and opens the detail page', async () => {
    mockApi();
    const { container } = renderWithProviders(<AlgorithmRoutes />, { path: '/algorithms/*', route: '/algorithms' });
    const demo = await screen.findByTestId('algorithm-card-research_demo_optimizer');
    expect(within(demo).getByText('接入验证算法 Integration Demo')).toBeTruthy();
    expect(within(demo).getByText('Not Learning Algorithm')).toBeTruthy();
    const grid = screen.getByTestId('algorithm-card-grid_search');
    expect(within(grid).getByText('工程基线 Engineering Baseline')).toBeTruthy();
    expect(screen.getByText(/Algorithm SDK v0.1/)).toBeTruthy();
    for (const phrase of ['AI Optimizer', 'Intelligent Optimizer', 'Learning Optimizer']) {
      expect(container.textContent).not.toContain(phrase);
    }
    fireEvent.click(demo);
    expect(await screen.findByTestId('algorithm-capabilities')).toBeTruthy();
    expect(screen.getByText('initial_step')).toBeTruthy();
    const evidence = screen.getByTestId('algorithm-evidence');
    expect(within(evidence).getByText('OPT-DEMO0001')).toBeTruthy();
    expect(screen.getByTestId('algorithm-notice').textContent).toContain('不是项目科研成果');
  });

  it('shows the integration guide', async () => {
    mockApi();
    renderWithProviders(<AlgorithmRoutes />, { path: '/algorithms/*', route: '/algorithms/guide' });
    expect(await screen.findByTestId('integration-lifecycle')).toBeTruthy();
    expect(screen.getByText('suggest()')).toBeTruthy();
    expect(await screen.findByText('docs/algorithms/how-to-integrate-an-algorithm.md')).toBeTruthy();
    expect(screen.getByText('ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED')).toBeTruthy();
  });
});

describe('Acceptance Center', () => {
  it('shows discrete prerequisite statuses without any percentage and lists ineligible evidence', async () => {
    mockApi();
    const { container } = renderWithProviders(<AcceptancePage />, { path: '/acceptance', route: '/acceptance' });
    const status = await screen.findByTestId('acceptance-status');
    expect(within(status).getByText('未确认 Not Confirmed')).toBeTruthy();
    expect(within(status).getAllByText('无 Not Available')).toHaveLength(2);
    expect(await screen.findByText('EVD-OPT-DEMO0001')).toBeTruthy();
    expect(container.textContent).not.toMatch(/\d+\s*%/);
  });
});
