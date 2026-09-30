import { screen } from '@testing-library/react';

import { renderWithProviders } from '../../test/render';
import { Day13Page } from './index';

vi.mock('../../api/day13', () => ({
  useAMatrixLibraries: () => ({ isLoading: false, isError: false, data: [{ library_id: 'spread', family: '8_BEAM_FAMILY', source_file_name: 'a_matrix_spread.npy', source_artifact: 'sionnatest/a_matrix', source_hash: 'hash', entry_count: 1216, beam_types: { SSB: 1024 }, semantic_status: 'RELATIVE_RESPONSE_ONLY' }], refetch: vi.fn() }),
  useAMatrixProfiles: () => ({ isLoading: false, isError: false, data: [{ id: 'p1', alias: 'AAU test', library: 'spread', beam_type: 'SSB', multi_beam: true, entry_key: 'entry-0', keys_by_beam: { '0': 'entry-0' }, beam_ids: [0], aau_type: 'AAU5270E', coverage: 0, tilt_deg: -2, azimuth_deg: 0, normalize: true }] }),
  useAMatrixPattern: () => ({ isLoading: false, isError: false, data: { entry: { entry_key: 'entry-0', raw_shape: [91, 72], dtype: 'float64', beam_id: 0, beam_family: '8_BEAM_FAMILY', beam_type: 'SSB', aau_type: 'AAU5270E', source_file_name: 'a_matrix_spread.npy', source_hash: 'hash', mapping_status: 'CONFIRMED_BY_PROFILE', data_quality: { status: 'VALID', negative_count: 0, min_value: 0, max_value: 1 } }, angular_grid: { version: 'D13', elevation_min_deg: -90, elevation_max_deg: 90, elevation_step_deg: 2, elevation_count: 91, azimuth_min_deg: 0, azimuth_max_sample_deg: 355, azimuth_step_deg: 5, azimuth_count: 72, axis_order: ['elevation', 'azimuth'], convention_source: 'SIONNATEST_IMPLEMENTATION' }, normalization: { policy_id: 'PEAK_LINEAR_POWER_TO_RELATIVE', formula: 'x/max(x)', field_amplitude_formula: 'sqrt(x)', source_semantic_status: 'ABSOLUTE_RADIO_KPI_NOT_CALIBRATED' }, lookup_method: 'nearest_grid', normalized_response: [[1]], field_amplitude: [[1]] } }),
  useUETwinQuery: () => ({ isPending: false, data: null, mutate: vi.fn() }),
}));

describe('Day 13 A-Matrix and UE Twin page', () => {
  it('shows relative response and calibration boundary', () => {
    renderWithProviders(<Day13Page />);
    expect(screen.getByText('A 矩阵与 UE Twin')).toBeTruthy();
    expect(screen.getByText(/绝对无线 KPI 尚未校准/)).toBeTruthy();
    expect(screen.getByText(/归一化相对响应/)).toBeTruthy();
    expect(screen.queryByText('进入多小区 Radio View')).toBeNull();
  });
});
