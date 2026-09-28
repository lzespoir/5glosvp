import { Card, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { ReactNode } from 'react';

import type { OptimizationCandidate } from '../../types/optimization';
import { EMPTY, formatPercent, isNumber } from '../../utils/format';
import { component, formatObjective, formatPower } from '../../utils/optimization';

interface Row {
  key: string;
  label: ReactNode;
  render: (c: OptimizationCandidate | null) => ReactNode;
}

const ROWS: Row[] = [
  {
    key: 'coverage',
    label: <>SINR 覆盖比例 <span className="muted">C_sinr</span></>,
    render: (c) => {
      const covered = component(c, 'covered_cells');
      const total = component(c, 'num_cells');
      return (
        <>
          {formatPercent(component(c, 'sinr_coverage_ratio'), 2)}
          {isNumber(covered) && isNumber(total) && <div className="muted">{covered} / {total} cells</div>}
        </>
      );
    },
  },
  {
    key: 'threshold',
    label: <>SINR 阈值 τ <Tag color="gold">[A] Assumption</Tag></>,
    render: (c) => (isNumber(component(c, 'sinr_threshold_db')) ? `${component(c, 'sinr_threshold_db')} dB` : EMPTY),
  },
  { key: 'power', label: 'TX Power P', render: (c) => formatPower(component(c, 'tx_power_dbm')) },
  {
    key: 'bounds',
    label: <>功率归一化区间 <span className="muted">[P_min, P_max]</span></>,
    render: (c) => {
      const lo = component(c, 'power_min_dbm');
      const hi = component(c, 'power_max_dbm');
      return isNumber(lo) && isNumber(hi) ? `[${lo}, ${hi}] dBm` : EMPTY;
    },
  },
  {
    key: 'cost',
    label: <>功率代价 <span className="muted">c_P</span></>,
    render: (c) => formatObjective(component(c, 'normalized_power_cost'), 3),
  },
  {
    key: 'lambda',
    label: <>权重 λ <Tag color="gold">[A] Assumption</Tag></>,
    render: (c) => formatObjective(component(c, 'lambda_power'), 2),
  },
  {
    key: 'term',
    label: <>功率代价项 <span className="muted">λ·c_P</span></>,
    render: (c) => formatObjective(component(c, 'power_cost_term')),
  },
  {
    key: 'value',
    label: <strong>目标值 J</strong>,
    render: (c) => <strong>{formatObjective(c?.objective?.value)}</strong>,
  },
];

interface Props {
  baseline: OptimizationCandidate | null;
  best: OptimizationCandidate | null;
  formula: string | null;
}

/** 目标函数分解：所有分量由后端 Objective 计算并随候选保存。 */
export function ObjectiveBreakdown({ baseline, best, formula }: Props) {
  const columns: ColumnsType<Row> = [
    { title: '分量 Component', key: 'label', render: (_, r) => r.label },
    { title: '基线 Baseline', key: 'baseline', align: 'right', render: (_, r) => r.render(baseline) },
    { title: `最优 ${best?.candidate_id ?? 'Best'}`, key: 'best', align: 'right', render: (_, r) => r.render(best) },
  ];
  return (
    <Card
      size="small"
      className="fill-height"
      title={<span>目标函数分解 <span className="card-title-en">Objective Breakdown</span></span>}
    >
      {formula && (
        <div className="objective-formula">
          <code>{formula}</code>
        </div>
      )}
      <Table rowKey="key" size="small" pagination={false} columns={columns} dataSource={ROWS} />
    </Card>
  );
}
