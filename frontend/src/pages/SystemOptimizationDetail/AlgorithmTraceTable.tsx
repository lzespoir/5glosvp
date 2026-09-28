import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import type { AlgorithmTrace, TraceRound } from '../../types/algorithm';
import { formatParameter } from '../../utils/systemOptimization';

interface Props {
  trace: AlgorithmTrace;
  parameterId: string;
}

function stateText(state: Record<string, unknown>): string {
  const keys = ['mode', 'incumbent', 'step', 'direction'].filter((k) => k in state);
  if (keys.length === 0) return Object.keys(state).length ? JSON.stringify(state) : '—';
  return keys.map((k) => `${k}=${String(state[k])}`).join(' · ');
}

/** 每轮 suggest → evaluate → observe：建议、实际评价的候选、被预算拒绝的建议与算法自述的决策。 */
export function AlgorithmTraceTable({ trace, parameterId }: Props) {
  const value = (s: Record<string, number>) => formatParameter(s[parameterId]);
  const columns: ColumnsType<TraceRound> = [
    { title: '轮次 Round', dataIndex: 'round', width: 90 },
    { title: '轮前状态 State Before', key: 'before', render: (_, r) => <span className="muted">{stateText(r.state_before)}</span> },
    {
      title: `建议 Suggestions (${parameterId})`,
      key: 'suggestions',
      render: (_, r) => r.suggestions.map((s, i) => <Tag key={i}>{value(s)}</Tag>),
    },
    {
      title: '评价候选 Evaluated',
      key: 'evaluated',
      render: (_, r) => r.evaluated_candidate_ids.map((id) => <div key={id}><code>{id}</code></div>),
    },
    {
      title: '预算拒绝 Rejected',
      key: 'rejected',
      render: (_, r) => (r.rejected_suggestions.length ? r.rejected_suggestions.map((s, i) => <Tag key={i} color="orange">{value(s)}</Tag>) : '—'),
    },
    {
      title: '决策 Decision',
      key: 'decision',
      render: (_, r) => String(r.state_after.last_decision ?? stateText(r.state_after)),
    },
  ];
  return (
    <Table
      rowKey="round"
      size="small"
      pagination={false}
      columns={columns}
      dataSource={trace.rounds}
      scroll={{ x: true }}
      data-testid="algorithm-trace-table"
    />
  );
}
