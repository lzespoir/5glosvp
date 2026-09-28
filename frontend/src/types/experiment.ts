export type ExperimentStatus = 'created' | 'queued' | 'running' | 'succeeded' | 'failed';

export interface ScenarioRef {
  scenario_id: string;
  name_zh: string;
  name_en: string;
}

export interface BackendRef {
  id: string;
  version?: string | null;
}

export interface RuntimeView {
  scenario_load_seconds?: number | null;
  simulation_seconds?: number | null;
  artifact_export_seconds?: number | null;
  total_seconds?: number | null;
}

export interface ArtifactView {
  name: string;
  /** image | json | yaml | text | binary */
  type: string;
  media_type: string;
  description?: string | null;
  url: string;
}

export interface ProvenanceView {
  source_type: string | null;
  data_type_zh?: string | null;
  data_type_en?: string | null;
  engine?: string | null;
  generated?: boolean | null;
  measured?: boolean | null;
  tag?: string | null;
}

export interface ExperimentErrorView {
  code: string;
  message: string;
  type: string;
}

export interface StatusTransitionView {
  status: ExperimentStatus;
  at: string;
}

/** metrics 中单层 Radio Map 的统计（来自后端 layer_statistics）。 */
export interface LayerStatistics {
  metric: string;
  unit: string | null;
  num_cells: number;
  num_covered_cells: number;
  coverage_ratio: number;
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
}

/** 后端尚未实现的指标。 */
export interface NotAvailableMetric {
  status: 'not_available';
  reason: string;
}

/** OpenAPI 中 metrics 为自由对象；以下字段是当前后端实际返回的结构。 */
export interface ExperimentMetrics {
  radio_map?: LayerStatistics;
  radio_map_layers?: Record<string, LayerStatistics>;
  [key: string]: unknown;
}

export type ExperimentPurpose = 'manual' | 'optimization_baseline' | 'optimization_candidate';

export interface ExperimentResponse {
  experiment_id: string;
  name: string;
  status: ExperimentStatus;
  purpose?: ExperimentPurpose;
  optimization_id?: string | null;
  scenario: ScenarioRef;
  backend: BackendRef;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  runtime: RuntimeView;
  metrics?: ExperimentMetrics;
  artifacts?: ArtifactView[];
  provenance?: ProvenanceView | null;
  error?: ExperimentErrorView | null;
  warnings?: string[];
  status_history?: StatusTransitionView[];
}

export interface ExperimentList {
  items: ExperimentResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExperimentCreateRequest {
  name: string;
  scenario_id: string;
}
