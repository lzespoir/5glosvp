import type { ExperimentResponse, ExperimentStatus, LayerStatistics, NotAvailableMetric } from '../types/experiment';

export interface StatusMeta {
  zh: string;
  en: string;
  /** Ant Design Tag/Badge 语义色 */
  color: 'default' | 'processing' | 'success' | 'error';
}

export const EXPERIMENT_STATUSES: ExperimentStatus[] = ['created', 'queued', 'running', 'succeeded', 'failed'];

export function statusMeta(status: ExperimentStatus): StatusMeta {
  switch (status) {
    case 'created':
      return { zh: '已创建', en: 'Created', color: 'default' };
    case 'queued':
      return { zh: '排队中', en: 'Queued', color: 'processing' };
    case 'running':
      return { zh: '运行中', en: 'Running', color: 'processing' };
    case 'succeeded':
      return { zh: '成功', en: 'Succeeded', color: 'success' };
    case 'failed':
      return { zh: '失败', en: 'Failed', color: 'error' };
    default: {
      const unreachable: never = status;
      throw new Error(`Unknown experiment status: ${String(unreachable)}`);
    }
  }
}

export function isActiveStatus(status: ExperimentStatus): boolean {
  return status === 'created' || status === 'queued' || status === 'running';
}

/** HTTP 201 不代表仿真成功：只有 status === 'succeeded' 才算成功。 */
export function isExperimentSucceeded(exp: Pick<ExperimentResponse, 'status'>): boolean {
  return exp.status === 'succeeded';
}

export function isExperimentFailed(exp: Pick<ExperimentResponse, 'status'>): boolean {
  return exp.status === 'failed';
}

export type DataKind = 'simulation' | 'test_fixture' | 'unknown';

export interface DataTypeMeta {
  kind: DataKind;
  zh: string;
  en: string;
  color: string;
}

/** 数据来源展示：当前平台只有仿真生成数据与软件测试夹具，禁止显示为实测/现网数据。 */
export function dataTypeMeta(sourceType: string | null | undefined): DataTypeMeta {
  if (sourceType === 'simulation') {
    return { kind: 'simulation', zh: '仿真生成', en: 'Simulation Generated', color: 'blue' };
  }
  if (sourceType === 'test_fixture') {
    return { kind: 'test_fixture', zh: '测试数据', en: 'TEST FIXTURE', color: 'orange' };
  }
  return { kind: 'unknown', zh: '未知来源', en: sourceType ?? 'Unknown', color: 'default' };
}

export function isLayerStatistics(v: unknown): v is LayerStatistics {
  return typeof v === 'object' && v !== null && 'num_cells' in v && 'coverage_ratio' in v;
}

export function isNotAvailable(v: unknown): v is NotAvailableMetric {
  return typeof v === 'object' && v !== null && (v as { status?: unknown }).status === 'not_available';
}

export interface MetricLabel {
  zh: string;
  en: string;
}

const METRIC_LABELS: Record<string, MetricLabel> = {
  rss: { zh: '接收信号强度', en: 'RSS' },
  sinr: { zh: '信干噪比', en: 'SINR' },
  path_gain: { zh: '路径增益', en: 'Path Gain' },
};

export function metricLabel(metric: string): MetricLabel {
  return METRIC_LABELS[metric] ?? { zh: metric, en: metric };
}

/** 固定展示顺序；API 中其余层按原样追加。 */
export function orderedLayers(layers: Record<string, LayerStatistics> | undefined): LayerStatistics[] {
  if (!layers) return [];
  const preferred = ['rss', 'sinr', 'path_gain'];
  const names = [...preferred.filter((n) => n in layers), ...Object.keys(layers).filter((n) => !preferred.includes(n))];
  return names.map((n) => layers[n]).filter(isLayerStatistics);
}
