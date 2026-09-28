export interface ScenarioSummary {
  scenario_id: string;
  name_zh: string;
  name_en: string;
  backend: string;
}

export interface TransmitterView {
  id: string;
  position: number[];
  orientation?: number[] | null;
  power_dbm?: number | null;
}

export interface MeasurementAreaView {
  center: number[];
  size: number[];
  orientation: number[];
}

export interface RadioMapView {
  metric: string;
  cell_size: number[];
  measurement_area?: MeasurementAreaView | null;
  max_depth: number;
  samples_per_tx: number;
}

export interface ScenarioDetail extends ScenarioSummary {
  scene_name: string;
  frequency_hz: number;
  bandwidth_hz: number;
  random_seed: number;
  transmitters: TransmitterView[];
  radio_map: RadioMapView;
}
