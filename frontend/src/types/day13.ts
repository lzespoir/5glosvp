export interface AMatrixLibrary {
  library_id: string;
  family: string;
  source_file_name: string;
  source_artifact: string;
  source_hash: string;
  entry_count: number;
  beam_types: Record<string, number>;
  semantic_status: string;
}

export interface AMatrixProfile {
  id: string;
  alias: string;
  library: string;
  beam_type: string;
  multi_beam: boolean;
  entry_key: string;
  keys_by_beam: Record<string, string>;
  beam_ids: number[];
  aau_type: string;
  coverage: number;
  tilt_deg: number | null;
  azimuth_deg: number | null;
  normalize: boolean;
}

export interface AMatrixPattern {
  entry: {
    entry_key: string;
    raw_shape: number[];
    dtype: string;
    beam_id: number | null;
    beam_family: string;
    beam_type: string;
    aau_type: string | null;
    source_file_name: string;
    source_hash: string;
    mapping_status: string;
    data_quality: { status: string; negative_count: number; min_value: number; max_value: number };
  };
  angular_grid: {
    version: string;
    elevation_min_deg: number;
    elevation_max_deg: number;
    elevation_step_deg: number;
    elevation_count: number;
    azimuth_min_deg: number;
    azimuth_max_sample_deg: number;
    azimuth_step_deg: number;
    azimuth_count: number;
    axis_order: string[];
    convention_source: string;
  };
  normalization: {
    policy_id: string;
    formula: string;
    field_amplitude_formula: string;
    source_semantic_status: string;
  };
  lookup_method: string;
  normalized_response: number[][];
  field_amplitude: number[][];
}

export interface UETwinResult {
  ue_id: string;
  position: { x: number; y: number; z: number; coordinate_system: string; source: string };
  serving_cell_id: string | null;
  neighbor_cell_ids: string[];
  aau_id: string;
  aau_position: { x: number; y: number; z: number; coordinate_system: string; source: string };
  radio_geometry: { distance_3d_m: number; azimuth_deg: number; elevation_deg: number; coordinate_convention: string };
  beam_observations: Array<{ beam_id: number; entry_key: string; azimuth_deg: number; elevation_deg: number; normalized_response: number; rank: number; lookup_method: string }>;
  strongest_relative_beam_id: number | null;
  provenance: Record<string, unknown>;
  calibration_status: string;
}
