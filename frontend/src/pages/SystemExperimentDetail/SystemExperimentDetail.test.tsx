import { fireEvent, screen, within } from '@testing-library/react';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { renderWithProviders } from '../../test/render';
import { fixtureKpiDefinitions, fixtureSystemExperiment } from '../../test/systemFixtures';
import type { SystemExperimentResponse } from '../../types/system';
import { SystemExperimentDetailPage } from './index';

vi.mock('../../components/NetworkView', () => ({ NetworkView: () => <div data-testid="network-view" /> }));
vi.mock('../../components/UeThroughputChart', () => ({ UeThroughputChart: () => <div data-testid="tput-chart" /> }));

const FORBIDDEN = [/Real Network Performance/, /Actual 5G Throughput/, /Huawei Network Result/, /EDGE_USER_RATE_ACCEPTANCE/];

function renderDetail(exp: SystemExperimentResponse) {
  vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === `/system-experiments/${exp.experiment_id}`) return { data: exp } as AxiosResponse;
    if (url === '/kpis') return { data: { items: fixtureKpiDefinitions } } as AxiosResponse;
    throw new Error(`unexpected GET ${url}`);
  });
  return renderWithProviders(<SystemExperimentDetailPage />, {
    path: '/system/experiments/:experimentId',
    route: `/system/experiments/${exp.experiment_id}`,
  });
}

afterEach(() => vi.restoreAllMocks());

describe('SystemExperimentDetailPage', () => {
  it('shows header, boundary banner, model badge and backend KPI values', async () => {
    renderDetail(fixtureSystemExperiment());
    expect(await screen.findByText('EXP-5Y5TEM01')).toBeTruthy();
    expect(within(screen.getByTestId('scientific-boundary')).getByText('当前结果来自系统级仿真，不是华为实测网络数据。')).toBeTruthy();
    expect(screen.getAllByTestId('model-badge')[0]?.textContent).toBe('Sionna Simulation Generated');
    expect(within(screen.getByTestId('kpi-card-NETWORK_THROUGHPUT_V0_1')).getByText('70')).toBeTruthy();
    expect(within(screen.getByTestId('kpi-card-P5_UE_THROUGHPUT_V0_1')).getByText('1')).toBeTruthy();
    expect(screen.getByTestId('tput-chart')).toBeTruthy();
    expect(screen.getByTestId('network-view')).toBeTruthy();
    for (const re of FORBIDDEN) expect(screen.queryByText(re)).toBeNull();
  });

  it('shows — with a reason for unavailable UE fields instead of 0', async () => {
    renderDetail(fixtureSystemExperiment());
    const missing = await screen.findByTestId('missing-UE-003-sinr_eff_db_mean');
    expect(missing.textContent).toBe('—');
    expect(screen.getByTestId('missing-UE-003-mcs_index_mean').textContent).toBe('—');
  });

  it('opens the UE computation chain with real values and Not Available for missing ones', async () => {
    renderDetail(fixtureSystemExperiment());
    fireEvent.click(await screen.findByText('UE-003'));
    const chain = await screen.findByTestId('ue-chain');
    expect(within(chain).getAllByText(/Not Available/).length).toBeGreaterThanOrEqual(2);
    expect(within(chain).getByText(/UE_THROUGHPUT_V0_1/)).toBeTruthy();
    expect(within(chain).getByText('0.000 Mbps')).toBeTruthy();
  });

  it('opens the KPI detail modal with provenance, Measured No and Acceptance KPI No', async () => {
    renderDetail(fixtureSystemExperiment());
    fireEvent.click(await screen.findByTestId('kpi-card-P5_UE_THROUGHPUT_V0_1'));
    expect(await screen.findByTestId('p5-note')).toBeTruthy();
    expect(screen.getByText("numpy.percentile(T_u, 5, method='linear')")).toBeTruthy();
    expect(screen.getByText('formula of P5_UE_THROUGHPUT_V0_1')).toBeTruthy();
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('实测数据 Measured').closest('tr')?.textContent).toContain('No');
    expect(within(dialog).getByText('验收 KPI Acceptance KPI').closest('tr')?.textContent).toContain('No');
    expect(within(dialog).getByText('EXP-5Y5TEM01')).toBeTruthy();
  });

  it('shows unavailable KPIs as — with Not Available', async () => {
    const base = fixtureSystemExperiment();
    renderDetail({
      ...base,
      kpis: base.kpis.map((k) => (k.metric_id === 'NETWORK_THROUGHPUT_V0_1' ? { ...k, available: false, value: null, unavailable_reason: 'No active UE' } : k)),
    });
    const card = await screen.findByTestId('kpi-card-NETWORK_THROUGHPUT_V0_1');
    expect(within(card).getByText('—')).toBeTruthy();
    expect(within(card).getByText('Not Available')).toBeTruthy();
  });

  it('distinguishes fallback and fixture sources visually', async () => {
    const base = fixtureSystemExperiment();
    renderDetail({ ...base, backend: { ...base.backend, model_type: 'engineering_approximation', model_label: 'Fast Engineering Approximation' } });
    expect((await screen.findAllByTestId('model-badge'))[0]?.textContent).toBe('Fast Engineering Approximation');
    expect(screen.getByTestId('scientific-boundary').className).toContain('model-badge--approx');
  });

  it('shows the error for failed runs', async () => {
    renderDetail(fixtureSystemExperiment({
      status: 'failed', result: null, kpis: [],
      error: { code: 'INVALID_SYSTEM_SCENARIO', message: 'only 1 cell supported', type: 'InvalidSystemScenarioError' },
    }));
    expect(await screen.findByText('系统级仿真失败 System Simulation Failed')).toBeTruthy();
    expect(screen.getByText('INVALID_SYSTEM_SCENARIO')).toBeTruthy();
    expect(screen.queryByTestId('kpi-card-NETWORK_THROUGHPUT_V0_1')).toBeNull();
  });
});
