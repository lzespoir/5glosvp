import { Table, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Link } from 'react-router-dom';

import type { KpiStatistic, SystemOptimizationCandidate } from '../../types/systemOptimization';
import { formatSeconds } from '../../utils/format';
import { formatMbps, formatParameter } from '../../utils/systemOptimization';

interface Props {
  optimizationId: string;
  parameterId: string;
  baseline: SystemOptimizationCandidate | null;
  candidates: SystemOptimizationCandidate[];
  bestCandidateId: string | null;
}

function statCell(s: KpiStatistic | null) {
  if (!s) return '—';
  return s.n > 1 ? (
    <Tooltip title={`n=${s.n} · std ${s.std.toFixed(3)} · [${s.min.toFixed(2)}, ${s.max.toFixed(2)}]`}>
      {formatMbps(s.mean)}
    </Tooltip>
  ) : (
    formatMbps(s.mean)
  );
}

export function SystemCandidateTable({ optimizationId, parameterId, baseline, candidates, bestCandidateId }: Props) {
  const rows = baseline ? [baseline, ...candidates] : candidates;
  const columns: ColumnsType<SystemOptimizationCandidate> = [
    {
      title: '候选 Candidate',
      key: 'id',
      render: (_, c) => (
        <>
          <code>{c.candidate_id}</code>{' '}
          {c.is_baseline && <Tag color="gold">Baseline</Tag>}
          {c.candidate_id === bestCandidateId && <Tag color="success">Best</Tag>}
          {c.reused_baseline && <Tag>Reused Baseline</Tag>}
        </>
      ),
    },
    { title: `参数 ${parameterId}`, key: 'param', align: 'right', render: (_, c) => formatParameter(c.parameters[parameterId]) },
    {
      title: '实验 Experiment',
      key: 'exp',
      render: (_, c) =>
        c.experiment_ids.length
          ? c.experiment_ids.map((id) => (
              <div key={id}>
                <Link to={`/system/experiments/${id}`} state={{ fromOptimization: optimizationId }}>
                  <code>{id}</code>
                </Link>
              </div>
            ))
          : '—',
    },
    { title: '网络 Network', key: 'net', align: 'right', render: (_, c) => statCell(c.network_throughput_mbps) },
    { title: '平均 Average', key: 'avg', align: 'right', render: (_, c) => statCell(c.average_ue_throughput_mbps) },
    { title: 'P5', key: 'p5', align: 'right', render: (_, c) => statCell(c.p5_ue_throughput_mbps) },
    {
      title: '目标 Objective',
      key: 'obj',
      align: 'right',
      render: (_, c) => (c.objective ? c.objective.value.toFixed(4) : '—'),
    },
    { title: '耗时 Runtime', key: 'rt', align: 'right', render: (_, c) => formatSeconds(c.runtime_seconds, 1) },
    {
      title: '状态 Status',
      key: 'status',
      render: (_, c) =>
        c.status === 'evaluated' ? (
          <Tag color="green">evaluated</Tag>
        ) : (
          <Tooltip title={c.error ? `${c.error.code}: ${c.error.message}` : undefined}>
            <Tag color="error">failed</Tag>
          </Tooltip>
        ),
    },
  ];
  return (
    <Table
      rowKey="candidate_id"
      size="small"
      pagination={false}
      columns={columns}
      dataSource={rows}
      rowClassName={(c) => (c.candidate_id === bestCandidateId ? 'candidate-row--best' : '')}
      scroll={{ x: true }}
      data-testid="candidate-table"
    />
  );
}
