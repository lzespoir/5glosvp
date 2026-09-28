import { Collapse, Descriptions, Tag } from 'antd';

import type { SystemExperimentResponse } from '../../types/system';
import { formatSeconds } from '../../utils/format';

function kv(obj: Record<string, unknown> | null | undefined) {
  if (!obj) return <span className="muted">Not Available</span>;
  return (
    <Descriptions column={1} size="small">
      {Object.entries(obj).map(([k, v]) => (
        <Descriptions.Item key={k} label={k}>
          {Array.isArray(v) ? v.join(', ') : typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)}
        </Descriptions.Item>
      ))}
    </Descriptions>
  );
}

function no() {
  return <Tag>No 否</Tag>;
}

/** 数据来源与高级信息（调度、链路自适应、功率分配、版本、UE 生成、假设）。 */
export function SystemProvenance({ experiment }: { experiment: SystemExperimentResponse }) {
  const r = experiment.result;
  const p = experiment.provenance;
  return (
    <>
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="结果来源 Result Source">{experiment.backend.model_label ?? p.model_label ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="数据类型 Source Type">{experiment.backend.source_type ?? p.source_type ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="提供方 Provider">{p.provider ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="实测数据 Measured">{no()}</Descriptions.Item>
        <Descriptions.Item label="华为数据 Huawei Data">{no()}</Descriptions.Item>
        <Descriptions.Item label="验收证据 Acceptance Evidence">{no()}</Descriptions.Item>
        <Descriptions.Item label="计算设备 Compute Device">{r?.compute_device ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="仿真时长 Simulated Time">
          {r ? `${r.num_slots} slots × ${r.slot_duration_s * 1e3} ms = ${formatSeconds(r.simulated_duration_s, 3)}` : '—'}
        </Descriptions.Item>
      </Descriptions>
      <Collapse
        className="section"
        size="small"
        items={[
          { key: 'scheduler', label: '调度器 Scheduler', children: kv(r?.scheduler) },
          { key: 'la', label: '链路自适应 Link Adaptation', children: kv(r?.link_adaptation) },
          { key: 'pc', label: '功率分配 Power Control / Precoding', children: kv(r?.power_control) },
          { key: 'ue', label: 'UE 生成 UE Generation', children: kv(r?.ue_generation) },
          { key: 'versions', label: '软件版本 Provider Versions', children: kv(r?.provider_versions) },
          {
            key: 'assumptions',
            label: '假设 Assumptions',
            children: (
              <ul className="plain-list">
                {(p.assumptions ?? []).map((a) => <li key={a}>{a}</li>)}
              </ul>
            ),
          },
        ]}
      />
    </>
  );
}
