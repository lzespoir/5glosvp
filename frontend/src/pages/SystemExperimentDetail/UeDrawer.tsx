import { Descriptions, Drawer, Steps } from 'antd';
import type { ReactNode } from 'react';

import { SystemModelBadge } from '../../components/SystemModelBadge';
import type { SystemModelType, SystemSimulationResult, UserEquipmentResult } from '../../types/system';
import { formatPercent, formatSeconds, formatVector, isNumber } from '../../utils/format';
import type { UeField } from '../../utils/system';
import { unavailableReason } from '../../utils/system';

interface Props {
  ue: UserEquipmentResult;
  result: SystemSimulationResult;
  modelType: SystemModelType | null;
  onClose: () => void;
}

const NOT_AVAILABLE = 'Not Available';

function fieldText(ue: UserEquipmentResult, field: UeField, digits: number, unit?: string): ReactNode {
  const v = ue[field];
  if (!isNumber(v)) {
    return (
      <span className="value-missing">
        {NOT_AVAILABLE} <span className="muted">· {unavailableReason(ue, field)}</span>
      </span>
    );
  }
  return unit ? `${v.toFixed(digits)} ${unit}` : v.toFixed(digits);
}

/** UE 计算链：全部为后端返回的真实值，缺失即显示 Not Available，前端不推算。 */
export function UeDrawer({ ue, result, modelType, onClose }: Props) {
  const steps = [
    {
      title: '位置 Position',
      description: `${formatVector(ue.position, 'm', 1)} · 服务小区 ${ue.serving_cell_id}`,
    },
    {
      title: '传播 Propagation',
      description: <>平均信道增益 Mean channel gain：{fieldText(ue, 'mean_channel_gain_db', 2, 'dB')}</>,
    },
    {
      title: '调度 Scheduling',
      description: (
        <>
          被调度时隙 {ue.scheduled_slots} / {result.num_slots} · 平均分配 {Math.round(ue.allocated_re_per_slot_mean).toLocaleString()} RE/slot（
          {formatPercent(ue.allocated_re_share, 1)}）· 平均发射功率 {fieldText(ue, 'tx_power_w_mean', 3, 'W')}
        </>
      ),
    },
    {
      title: 'PHY：SINR',
      description: <>有效 SINR（被调度时隙均值）：{fieldText(ue, 'sinr_eff_db_mean', 2, 'dB')}</>,
    },
    {
      title: '链路自适应 Link Adaptation',
      description: <>MCS 均值：{fieldText(ue, 'mcs_index_mean', 2)} · MCS 表 {String(result.link_adaptation.mcs_table_index ?? '—')}</>,
    },
    {
      title: '译码 Decoding (PHY Abstraction)',
      description: (
        <>
          ACK 时隙 {ue.acked_slots} / {ue.scheduled_slots} · TBLER {fieldText(ue, 'tbler', 3)} · 成功译码比特 {ue.decoded_bits.toLocaleString()} bit
        </>
      ),
    },
    {
      title: 'UE 吞吐率 Throughput',
      description: (
        <>
          <code>{ue.throughput_metric_id ?? 'UE_THROUGHPUT_V0_1'}</code>：{ue.decoded_bits.toLocaleString()} bit /{' '}
          {formatSeconds(ue.simulated_duration_s, 3)} = <strong>{fieldText(ue, 'throughput_mbps', 3, 'Mbps')}</strong>
          <div className="muted">数值由后端 KPI 引擎计算 · Computed by the backend KPI engine</div>
        </>
      ),
    },
  ];

  return (
    <Drawer
      open
      onClose={onClose}
      size={560}
      title={
        <span>
          <code>{ue.ue_id}</code> 计算链 <span className="card-title-en">Computation Chain</span>
        </span>
      }
    >
      <Steps orientation="vertical" size="small" current={steps.length} items={steps} data-testid="ue-chain" />
      <Descriptions column={1} size="small" bordered className="section" title="原始字段 Raw Fields">
        <Descriptions.Item label="decoded_bits">{ue.decoded_bits}</Descriptions.Item>
        <Descriptions.Item label="simulated_duration_s">{ue.simulated_duration_s}</Descriptions.Item>
        <Descriptions.Item label="scheduled / acked slots">{ue.scheduled_slots} / {ue.acked_slots}</Descriptions.Item>
        <Descriptions.Item label="allocated_re_share">{ue.allocated_re_share.toFixed(4)}</Descriptions.Item>
        <Descriptions.Item label="数据来源 Source">
          <SystemModelBadge modelType={modelType} /> Measured: No · Acceptance KPI: No
        </Descriptions.Item>
      </Descriptions>
    </Drawer>
  );
}
