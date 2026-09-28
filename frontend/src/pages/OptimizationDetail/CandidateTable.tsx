import { Card, Space, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Link } from 'react-router-dom';

import type { OptimizationCandidate } from '../../types/optimization';
import { formatPercent, formatSeconds } from '../../utils/format';
import { candidatePower, component, formatObjective, formatPower } from '../../utils/optimization';

interface Props {
  baseline: OptimizationCandidate | null;
  candidates: OptimizationCandidate[];
  bestCandidateId: string | null;
}

export function CandidateTable({ baseline, candidates, bestCandidateId }: Props) {
  const rows = [...(baseline ? [baseline] : []), ...candidates];
  const columns: ColumnsType<OptimizationCandidate> = [
    {
      title: '候选 Candidate',
      key: 'id',
      render: (_, c) => (
        <Space size={4} wrap>
          <code>{c.candidate_id}</code>
          {c.is_baseline && <Tag color="gold">BASELINE 基线</Tag>}
          {c.candidate_id === bestCandidateId && <Tag color="green">BEST</Tag>}
          {c.reused_baseline && <Tag>Reused Baseline 复用基线结果</Tag>}
        </Space>
      ),
    },
    { title: 'TX Power', key: 'power', align: 'right', render: (_, c) => formatPower(candidatePower(c)) },
    {
      title: 'SINR Coverage',
      key: 'coverage',
      align: 'right',
      render: (_, c) => formatPercent(component(c, 'sinr_coverage_ratio'), 2),
    },
    {
      title: 'Power Cost c_P',
      key: 'cost',
      align: 'right',
      render: (_, c) => formatObjective(component(c, 'normalized_power_cost'), 3),
    },
    {
      title: 'Objective J',
      key: 'objective',
      align: 'right',
      render: (_, c) => (c.status === 'failed' ? <Tag color="red">失败 Failed</Tag> : formatObjective(c.objective?.value)),
    },
    { title: '仿真耗时 Runtime', key: 'runtime', align: 'right', render: (_, c) => formatSeconds(c.runtime_seconds, 2) },
    {
      title: '实验 Experiment',
      key: 'experiment',
      render: (_, c) =>
        c.experiment_id ? (
          <Link to={`/experiments/${c.experiment_id}`} data-testid={`experiment-link-${c.candidate_id}`}>
            <code>{c.experiment_id}</code>
          </Link>
        ) : (
          '—'
        ),
    },
  ];
  return (
    <Card size="small" title={<span>候选评价 <span className="card-title-en">Candidate Table</span></span>}>
      <Table
        rowKey="candidate_id"
        size="small"
        pagination={false}
        columns={columns}
        dataSource={rows}
        rowClassName={(c) => (c.candidate_id === bestCandidateId ? 'candidate-row--best' : '')}
        expandable={{
          rowExpandable: (c) => !!c.error,
          expandedRowRender: (c) => (c.error ? <span><code>{c.error.code}</code> · {c.error.message}</span> : null),
        }}
      />
    </Card>
  );
}
