import type { KpiResult, SystemModelType, UserEquipmentResult } from '../types/system';

export const UE_THROUGHPUT = 'UE_THROUGHPUT_V0_1';
export const NETWORK_THROUGHPUT = 'NETWORK_THROUGHPUT_V0_1';
export const AVG_UE_THROUGHPUT = 'AVG_UE_THROUGHPUT_V0_1';
export const P5_UE_THROUGHPUT = 'P5_UE_THROUGHPUT_V0_1';

export const SCIENTIFIC_BOUNDARY = '当前结果来自系统级仿真，不是华为实测网络数据。';
export const P5_EDGE_NOTE = 'P5 UE Throughput 尚未确认等同于项目验收中的"边缘用户速率"。';

export interface ModelMeta {
  label: string;
  labelZh: string;
  color: string;
  className: string;
}

export function modelMeta(modelType: SystemModelType | null | undefined): ModelMeta {
  if (!modelType) {
    return { label: 'Unknown Source', labelZh: '来源未知', color: 'default', className: 'model-badge--unknown' };
  }
  switch (modelType) {
    case 'sionna_sys':
      return { label: 'Sionna Simulation Generated', labelZh: 'Sionna 仿真生成', color: 'blue', className: 'model-badge--sionna' };
    case 'engineering_approximation':
      return {
        label: 'Fast Engineering Approximation',
        labelZh: '快速工程近似',
        color: 'orange',
        className: 'model-badge--approx',
      };
    case 'test_fixture':
      return { label: 'TEST FIXTURE', labelZh: '软件测试夹具', color: 'red', className: 'model-badge--fixture' };
    default: {
      const unreachable: never = modelType;
      return { label: String(unreachable), labelZh: String(unreachable), color: 'default', className: 'model-badge--unknown' };
    }
  }
}

export function findKpi(kpis: KpiResult[], metricId: string): KpiResult | undefined {
  return kpis.find((k) => k.metric_id === metricId);
}

export type UeField = keyof Pick<
  UserEquipmentResult,
  'mean_channel_gain_db' | 'sinr_eff_db_mean' | 'mcs_index_mean' | 'tbler' | 'tx_power_w_mean' | 'throughput_mbps'
>;

/** 值缺失时返回后端给出的原因（前端不补 0、不推算）。 */
export function unavailableReason(ue: UserEquipmentResult, field: UeField): string {
  return ue.unavailable[field] ?? '后端未返回该值 / Not returned by backend';
}
