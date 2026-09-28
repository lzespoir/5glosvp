import { artifactAction } from '../components/ArtifactsPanel';
import { layer } from '../test/fixtures';
import { formatDateTime, formatHz, formatPercent, formatSeconds, formatValue, formatVector } from './format';
import {
  EXPERIMENT_STATUSES,
  dataTypeMeta,
  isActiveStatus,
  isExperimentFailed,
  isExperimentSucceeded,
  isNotAvailable,
  orderedLayers,
  statusMeta,
} from './status';

describe('statusMeta', () => {
  it('maps every status to Chinese label and semantic color', () => {
    expect(EXPERIMENT_STATUSES.map((s) => statusMeta(s).zh)).toEqual(['已创建', '排队中', '运行中', '成功', '失败']);
    expect(EXPERIMENT_STATUSES.map((s) => statusMeta(s).color)).toEqual([
      'default',
      'processing',
      'processing',
      'success',
      'error',
    ]);
  });

  it('treats only succeeded as success, regardless of HTTP status', () => {
    expect(isExperimentSucceeded({ status: 'succeeded' })).toBe(true);
    expect(isExperimentSucceeded({ status: 'failed' })).toBe(false);
    expect(isExperimentFailed({ status: 'failed' })).toBe(true);
    expect(isActiveStatus('running')).toBe(true);
    expect(isActiveStatus('failed')).toBe(false);
  });
});

describe('dataTypeMeta', () => {
  it('never labels test fixtures as simulation data', () => {
    expect(dataTypeMeta('simulation').en).toBe('Simulation Generated');
    expect(dataTypeMeta('test_fixture').en).toBe('TEST FIXTURE');
    expect(dataTypeMeta(null).kind).toBe('unknown');
  });
});

describe('metrics helpers', () => {
  it('orders layers rss, sinr, path_gain then extras', () => {
    const layers = {
      path_gain: layer('path_gain', 'dB', -100),
      extra: layer('extra', 'dB', 1),
      rss: layer('rss', 'dBm', -60),
      sinr: layer('sinr', 'dB', 10),
    };
    expect(orderedLayers(layers).map((l) => l.metric)).toEqual(['rss', 'sinr', 'path_gain', 'extra']);
    expect(orderedLayers(undefined)).toEqual([]);
  });

  it('detects not_available metrics', () => {
    expect(isNotAvailable({ status: 'not_available', reason: 'x' })).toBe(true);
    expect(isNotAvailable(layer('rss', 'dBm', 1))).toBe(false);
  });
});

describe('format', () => {
  it('formats values and falls back to em dash', () => {
    expect(formatSeconds(0.0401)).toBe('0.040 s');
    expect(formatSeconds(null)).toBe('—');
    expect(formatHz(3.5e9)).toBe('3.5 GHz');
    expect(formatHz(1e8)).toBe('100 MHz');
    expect(formatHz(undefined)).toBe('—');
    expect(formatPercent(0.5766)).toBe('57.7%');
    expect(formatValue(-62.95, 'dBm')).toBe('-63.0 dBm');
    expect(formatVector([-150.3, 21.63, 42.5])).toBe('(-150.3, 21.63, 42.5)');
    expect(formatVector([])).toBe('—');
    expect(formatDateTime('not a date')).toBe('—');
  });
});

describe('artifactAction', () => {
  it('views images, opens text, downloads binaries', () => {
    expect(artifactAction({ name: 'radio_map.png', type: 'image', media_type: 'image/png' })).toBe('view');
    expect(artifactAction({ name: 'result.json', type: 'json', media_type: 'application/json' })).toBe('open');
    expect(artifactAction({ name: 'config.yaml', type: 'yaml', media_type: 'application/yaml' })).toBe('open');
    expect(artifactAction({ name: 'run.log', type: 'text', media_type: 'text/plain' })).toBe('open');
    expect(artifactAction({ name: 'radio_map.npz', type: 'binary', media_type: 'application/octet-stream' })).toBe(
      'download',
    );
  });
});
