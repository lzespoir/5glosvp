import { fireEvent, screen, waitFor } from '@testing-library/react';

import { renderWithProviders } from '../../test/render';
import { scenarioCandidatesApi } from '../../api/scenarioCandidates';
import { ScenariosPage } from './index';

vi.mock('../../api/scenarioSystem', () => ({
  useScenarioTaxonomy: () => ({ isLoading: false, isError: false, data: {
    taxonomy_version: '0.1',
    dimensions: [{ key: 'environment', label_zh: '环境', label_en: 'Environment', options: [{ value: 'dense_urban', label_zh: '密集城区', label_en: 'Dense urban', status: 'SUPPORTED' }] }],
    families: [],
  }, refetch: vi.fn() }),
}));

vi.mock('../../api/scenarioCandidates', () => ({
  scenarioCandidatesApi: {
    preview: vi.fn(),
    promote: vi.fn(),
  },
}));

describe('Scenario Candidate Builder', () => {
  it('keeps candidate preview distinct from persisted definitions and experiments', () => {
    renderWithProviders(<ScenariosPage />);
    expect(screen.getByText('候选场景组合器')).toBeTruthy();
    expect(screen.getByText('候选 ≠ 已配置场景 ≠ 实验')).toBeTruthy();
    expect((screen.getByRole('button', { name: '生成候选预览' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByText('场景库 Catalog')).toBeNull();
    expect(screen.queryByText('验收映射 Acceptance')).toBeNull();
    expect(screen.getByText('选择至少一项')).toBeTruthy();
  });

  it('requests a stateless preview only after a taxonomy value is selected', async () => {
    const candidate = {
      candidate_id: 'CAND-TEST', candidate_hash: 'hash', taxonomy_version: '0.1', name_zh: '密集城区候选', name_en: 'Dense urban candidate',
      scenario_family: 'coverage_structure', dimensions: { environment: 'dense_urban' }, compatibility_status: 'VALID_EXECUTABLE',
      support_status: 'SUPPORTED', supported_problem_types: ['NETWORK_STRUCTURE'], source: 'CANDIDATE_ASSISTANT', acceptance_eligible: false as const,
    };
    vi.mocked(scenarioCandidatesApi.preview).mockResolvedValue({
      theoretical_count: 1, valid_candidate_count: 1, invalid_candidate_count: 0, executable_candidate_count: 1,
      external_dependency_candidate_count: 0, returned_count: 1, truncated: false, items: [candidate], persisted: false, configured_count_changed: false,
    });
    renderWithProviders(<ScenariosPage />);

    const generate = screen.getByRole('button', { name: '生成候选预览' });
    expect((generate as HTMLButtonElement).disabled).toBe(true);
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(await screen.findByText('密集城区 · SUPPORTED', { selector: '.ant-select-item-option-content' }));
    const readyButton = screen.getByRole('button', { name: '生成候选预览' });
    await waitFor(() => expect((readyButton as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(readyButton);

    expect(scenarioCandidatesApi.preview).toHaveBeenCalledWith({ environment: ['dense_urban'] }, 50);
    expect(await screen.findByText('候选预览 · 1 条（未保存）')).toBeTruthy();
    expect(screen.getByText(/Day12 组合规则分类/)).toBeTruthy();
  });
});
