import { Alert, Descriptions, Modal, Tag } from 'antd';

import type { KpiDefinition, KpiResult } from '../../types/system';
import { formatValue } from '../../utils/format';
import { P5_EDGE_NOTE, P5_UE_THROUGHPUT } from '../../utils/system';

interface Props {
  kpi: KpiResult | undefined;
  definition: KpiDefinition | undefined;
  metricId: string;
  onClose: () => void;
}

function yesNo(v: boolean) {
  return v ? <Tag color="red">Yes 是</Tag> : <Tag>No 否</Tag>;
}

/** KPI 详情：展示后端 KPI 引擎给出的定义与溯源，前端不做任何计算。 */
export function KpiDetailModal({ kpi, definition, metricId, onClose }: Props) {
  return (
    <Modal
      open
      onCancel={onClose}
      footer={null}
      width={720}
      title={<span>KPI 详情 <span className="card-title-en">KPI Detail</span></span>}
    >
      {metricId === P5_UE_THROUGHPUT && (
        <Alert type="warning" showIcon className="section-bottom" title={P5_EDGE_NOTE} data-testid="p5-note" />
      )}
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="Metric ID"><code>{metricId}</code></Descriptions.Item>
        <Descriptions.Item label="版本 Version">{kpi?.version ?? definition?.version ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="名称 Name">
          {definition ? `${definition.name_zh} / ${definition.name_en}` : kpi ? `${kpi.name_zh} / ${kpi.name_en}` : '—'}
        </Descriptions.Item>
        <Descriptions.Item label="定义 Definition">
          {definition ? (
            <>
              <code>{definition.formula}</code>
              <div className="muted">{definition.measurement_method}</div>
            </>
          ) : (
            'Not Available'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="数值 Value">
          {kpi?.available ? formatValue(kpi.value, kpi.unit, 3) : `— · ${kpi?.unavailable_reason ?? 'Not Available'}`}
        </Descriptions.Item>
        <Descriptions.Item label="单位 Unit">{kpi?.unit ?? definition?.unit ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="计算方法 Calculation">
          {kpi ? <code>{kpi.calculation_method}</code> : '—'}
          {kpi && <span className="muted"> · 样本数 n = {kpi.sample_size}</span>}
        </Descriptions.Item>
        <Descriptions.Item label="来源实验 Source Experiment">{kpi ? <code>{kpi.source_experiment}</code> : '—'}</Descriptions.Item>
        <Descriptions.Item label="后端 Backend">{kpi?.backend ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="场景 Scenario">{kpi?.scenario_id ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="随机种子 Seed">{kpi?.seed ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="数据来源 Source Type">{kpi?.source_type ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="假设 Assumptions">
          {(kpi?.assumptions ?? definition?.assumptions ?? []).length > 0 ? (
            <ul className="plain-list">
              {(kpi?.assumptions ?? definition?.assumptions ?? []).map((a) => <li key={a}>{a}</li>)}
            </ul>
          ) : (
            '—'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="实测数据 Measured">{yesNo(kpi?.measured ?? false)}</Descriptions.Item>
        <Descriptions.Item label="验收 KPI Acceptance KPI">{yesNo(kpi?.acceptance_kpi ?? false)}</Descriptions.Item>
        {definition && (
          <Descriptions.Item label="文档 Document"><code>{definition.doc}</code></Descriptions.Item>
        )}
      </Descriptions>
    </Modal>
  );
}
