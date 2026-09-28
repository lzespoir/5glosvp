import { screen } from '@testing-library/react';
import type { AxiosResponse } from 'axios';

import { apiClient } from '../../api/client';
import { failedExperiment, succeededExperiment } from '../../test/fixtures';
import { renderWithProviders } from '../../test/render';
import type { ExperimentResponse } from '../../types/experiment';
import { ExperimentDetailPage } from '.';

function mockGet(exp: ExperimentResponse) {
  vi.spyOn(apiClient, 'get').mockResolvedValue({ data: exp, status: 200 } as AxiosResponse);
}

function renderDetail(id: string) {
  return renderWithProviders(<ExperimentDetailPage />, {
    path: '/experiment-under-test/:experimentId',
    route: `/experiment-under-test/${id}`,
  });
}

afterEach(() => vi.restoreAllMocks());

describe('ExperimentDetailPage', () => {
  it('renders metrics, placeholder KPIs and provenance for a succeeded experiment', async () => {
    mockGet(succeededExperiment());
    renderDetail('EXP-AAAA0001');

    expect(await screen.findAllByText('EXP-AAAA0001')).not.toHaveLength(0);
    expect(screen.getByText('RSS')).toBeTruthy();
    expect(screen.getByText('SINR')).toBeTruthy();
    expect(screen.getByText('Path Gain')).toBeTruthy();
    expect(screen.getByText('Radio Map Coverage')).toBeTruthy();

    expect(screen.getByText('尚未接入系统级模型')).toBeTruthy();
    expect(screen.getByText('验收口径待冻结')).toBeTruthy();
    expect(screen.getByText('当前 Radio Map 提供 RSS，不等同于 RSRP')).toBeTruthy();
    expect(screen.queryByText(/\+\d+%/)).toBeNull();

    expect(screen.getByText(/不属于华为实测数据或运营商现网数据/)).toBeTruthy();
    expect(screen.getByText('否 No')).toBeTruthy();

    expect(screen.getByRole('button', { name: /查看 View/ })).toBeTruthy();
    expect(screen.getByRole('link', { name: /打开 Open/ })).toBeTruthy();
    expect(screen.getByRole('link', { name: /下载 Download/ })).toBeTruthy();
  });

  it('still opens a failed experiment and shows its error and timeline', async () => {
    mockGet(failedExperiment());
    renderDetail('EXP-FFFF0001');

    expect(await screen.findByText('实验执行失败 Experiment Failed')).toBeTruthy();
    expect(screen.getByText('SIMULATION_FAILED')).toBeTruthy();
    expect(screen.getByText(/ray tracer exploded/)).toBeTruthy();
    expect(screen.getAllByText('失败').length).toBeGreaterThan(0);
    expect(screen.getByText('已创建')).toBeTruthy();
    expect(screen.getByText(/实验失败，未产生仿真指标/)).toBeTruthy();
    expect(screen.getByText('暂无产物 / No artifacts')).toBeTruthy();
  });
});
