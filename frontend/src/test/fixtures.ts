import type { ExperimentResponse, LayerStatistics } from '../types/experiment';

export function layer(metric: string, unit: string, mean: number): LayerStatistics {
  return {
    metric,
    unit,
    num_cells: 100,
    num_covered_cells: 58,
    coverage_ratio: 0.58,
    min: mean - 40,
    max: mean + 30,
    mean,
    median: mean,
  };
}

export function succeededExperiment(overrides: Partial<ExperimentResponse> = {}): ExperimentResponse {
  const rss = layer('rss', 'dBm', -63);
  return {
    experiment_id: 'EXP-AAAA0001',
    name: 'test',
    status: 'succeeded',
    scenario: { scenario_id: 'SIONNA-DEMO-001', name_zh: '内置场景', name_en: 'Built-in Scene' },
    backend: { id: 'sionna_rt', version: '2.1.0' },
    created_at: '2026-09-28T04:00:46+00:00',
    started_at: '2026-09-28T04:00:46+00:00',
    finished_at: '2026-09-28T04:00:48+00:00',
    runtime: { scenario_load_seconds: 0.3, simulation_seconds: 0.04, artifact_export_seconds: 0.27, total_seconds: 0.67 },
    metrics: {
      radio_map: rss,
      radio_map_layers: { rss, path_gain: layer('path_gain', 'dB', -107), sinr: layer('sinr', 'dB', 20) },
      rsrp: { status: 'not_available', reason: 'RSRP not implemented' },
    },
    artifacts: [
      { name: 'radio_map.png', type: 'image', media_type: 'image/png', description: 'Radio map', url: '/api/v1/experiments/EXP-AAAA0001/artifacts/radio_map.png' },
      { name: 'result.json', type: 'json', media_type: 'application/json', description: null, url: '/api/v1/experiments/EXP-AAAA0001/artifacts/result.json' },
      { name: 'radio_map.npz', type: 'binary', media_type: 'application/octet-stream', description: null, url: '/api/v1/experiments/EXP-AAAA0001/artifacts/radio_map.npz' },
    ],
    provenance: {
      source_type: 'simulation',
      data_type_zh: '仿真生成',
      data_type_en: 'Simulation Generated',
      engine: 'Sionna RT',
      generated: true,
      measured: false,
      tag: 'G',
    },
    error: null,
    warnings: [],
    status_history: [
      { status: 'created', at: '2026-09-28T04:00:46+00:00' },
      { status: 'running', at: '2026-09-28T04:00:46+00:00' },
      { status: 'succeeded', at: '2026-09-28T04:00:48+00:00' },
    ],
    ...overrides,
  };
}

export function failedExperiment(): ExperimentResponse {
  return succeededExperiment({
    experiment_id: 'EXP-FFFF0001',
    status: 'failed',
    runtime: { total_seconds: 0.1 },
    metrics: {},
    artifacts: [],
    error: { code: 'SIMULATION_FAILED', message: 'ray tracer exploded', type: 'RuntimeError' },
    status_history: [
      { status: 'created', at: '2026-09-28T04:00:46+00:00' },
      { status: 'running', at: '2026-09-28T04:00:46+00:00' },
      { status: 'failed', at: '2026-09-28T04:00:47+00:00' },
    ],
  });
}
