import { screen } from '@testing-library/react';

import { renderWithProviders } from '../../test/render';
import { ScenariosPage } from './index';

vi.mock('../../api/scenarioSystem', () => ({
  useScenarioTaxonomy: () => ({ isLoading: false, isError: false, isSuccess: true, data: {
    taxonomy_version: '0.1',
    dimensions: [{ key: 'environment', label_zh: '环境', label_en: 'Environment', options: [{ value: 'dense_urban', label_zh: '密集城区', label_en: 'Dense urban', status: 'SUPPORTED' }] }],
    families: [],
  }, refetch: vi.fn() }),
  useScenarioCatalog: () => ({ isLoading: false, isError: false, data: { total: 120, items: [{
    scenario_id: 'SCN-D12-TEST',
    name_zh: '密集城区 + 单站单小区',
    name_en: 'Dense urban',
    description: 'test',
    taxonomy_version: '0.1',
    scenario_family: 'coverage_structure',
    dimensions: { environment: 'dense_urban' },
    compatibility_status: 'VALID_EXECUTABLE',
    support_status: 'SUPPORTED',
    model_bindings: {},
    dataset_bindings: {},
    artifact_bindings: {},
    supported_problem_types: ['NETWORK_STRUCTURE'],
    source: 'test',
    version: '0.1',
    scenario_definition_hash: 'abc',
  }] }, refetch: vi.fn() }),
  useScenarioCoverage: () => ({ isLoading: false, isError: false, data: { counts: { theoretical_count: 137, valid_count: 137, invalid_count: 0, executable_count: 100, requires_external_asset_count: 12, materialized_count: 120, verified_count: 120 }, matrix: [], family_counts: {} }, refetch: vi.fn() }),
  useAcceptanceMapping: () => ({ isLoading: false, isError: false, data: [{ key: 'task', title_zh: '任务书 1.2', title_en: 'Task', status: '部分实现', evidence: ['catalog'], note_zh: '场景体系骨架已建立。' }], refetch: vi.fn() }),
  useScenarioPreview: () => ({ data: { counts: { theoretical_count: 137, valid_count: 137, invalid_count: 0, executable_count: 100, requires_external_asset_count: 12 }, combinations: [], truncated: true } }),
  useMaterializeScenario: () => ({ mutate: vi.fn(), isPending: false, data: null }),
}));

vi.mock('../../api/scenarios', () => ({ useScenarios: () => ({ isLoading: false, isError: false, data: [] }) }));
vi.mock('../../api/backends', () => ({ useBackends: () => ({ isSuccess: true, data: [] }) }));
vi.mock('./ScenarioCard', () => ({ ScenarioCard: () => <div>legacy scenario</div> }));

describe('Scenario Center', () => {
  it('shows semantic count separation and acceptance mapping', () => {
    renderWithProviders(<ScenariosPage />);
    expect(screen.getByText('场景中心')).toBeTruthy();
    expect(screen.getByText('理论组合')).toBeTruthy();
    expect(screen.getAllByText('137').length).toBeGreaterThan(0);
    expect(screen.getByText('验收映射 Acceptance')).toBeTruthy();
    expect(screen.getByText(/百余定义不等于/)).toBeTruthy();
  });
});
