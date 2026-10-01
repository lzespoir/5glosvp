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
      external_dependency_candidate_count: 0, filtered_candidate_count: 1, total: 1, offset: 0, limit: 20,
      returned_count: 1, has_more: false, truncated: false, query_hash: 'query-1', taxonomy_version: '0.1',
      items: [candidate], persisted: false, configured_count_changed: false, acceptance_eligible: false,
    });
    renderWithProviders(<ScenariosPage />);

    const generate = screen.getByRole('button', { name: '生成候选预览' });
    expect((generate as HTMLButtonElement).disabled).toBe(true);
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(await screen.findByText('密集城区 · SUPPORTED', { selector: '.ant-select-item-option-content' }));
    const readyButton = screen.getByRole('button', { name: '生成候选预览' });
    await waitFor(() => expect((readyButton as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(readyButton);

    expect(scenarioCandidatesApi.preview).toHaveBeenCalledWith({ environment: ['dense_urban'] }, { offset: 0, limit: 20, filters: {} });
    expect(await screen.findByText('候选预览 · 1 条（未保存）')).toBeTruthy();
    expect(screen.getByText(/Day12 组合规则分类/)).toBeTruthy();
  });

  it('requests the next candidate page from the server with the same query identity', async () => {
    const makeCandidate = (index: number) => ({
      candidate_id: `CAND-${index}`, candidate_hash: `hash-${index}`, taxonomy_version: '0.1', name_zh: `候选 ${index}`, name_en: `Candidate ${index}`,
      scenario_family: 'coverage_structure', dimensions: { environment: 'dense_urban' }, compatibility_status: 'VALID_EXECUTABLE',
      support_status: 'SUPPORTED', supported_problem_types: ['NETWORK_STRUCTURE'], source: 'CANDIDATE_ASSISTANT', acceptance_eligible: false as const,
    });
    const base = { theoretical_count: 21, valid_candidate_count: 21, invalid_candidate_count: 0, executable_candidate_count: 21,
      external_dependency_candidate_count: 0, filtered_candidate_count: 21, total: 21, limit: 20, has_more: true, truncated: true,
      query_hash: 'stable-query', taxonomy_version: '0.1', persisted: false as const, configured_count_changed: false as const, acceptance_eligible: false as const };
    vi.mocked(scenarioCandidatesApi.preview)
      .mockResolvedValueOnce({ ...base, offset: 0, returned_count: 20, items: Array.from({ length: 20 }, (_, index) => makeCandidate(index)) })
      .mockResolvedValueOnce({ ...base, offset: 20, returned_count: 1, has_more: false, truncated: false, items: [makeCandidate(20)] });
    renderWithProviders(<ScenariosPage />);
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(await screen.findByText('密集城区 · SUPPORTED', { selector: '.ant-select-item-option-content' }));
    fireEvent.click(screen.getByRole('button', { name: '生成候选预览' }));

    expect(await screen.findByText('候选预览 · 21 条（未保存）')).toBeTruthy();
    await waitFor(() => expect(scenarioCandidatesApi.preview).toHaveBeenCalledTimes(1));
    const nextPage = document.querySelector('.ant-pagination-next button');
    expect(nextPage).not.toBeNull();
    fireEvent.click(nextPage!);
    await waitFor(() => expect(scenarioCandidatesApi.preview).toHaveBeenCalledTimes(2));
    expect(scenarioCandidatesApi.preview).toHaveBeenLastCalledWith({ environment: ['dense_urban'] }, {
      offset: 20, limit: 20, filters: {}, query_hash: 'stable-query',
    });
    expect(await screen.findByText('候选 20')).toBeTruthy();
  });
});
