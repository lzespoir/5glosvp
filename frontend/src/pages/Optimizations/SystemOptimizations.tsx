import { Alert, Button, Card, Col, Descriptions, Empty, Row, Skeleton, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAlgorithms } from '../../api/algorithms';
import {
  useBenchmarkProtocols,
  useSystemObjectives,
  useSystemOptimizations,
  useSystemParameters,
} from '../../api/systemOptimizations';
import { ErrorState } from '../../components/ErrorState';
import { StatusTag } from '../../components/StatusTag';
import type { BenchmarkProtocol, SystemObjectiveView, SystemOptimizationResponse } from '../../types/systemOptimization';
import { formatDateTime, formatSeconds } from '../../utils/format';
import {
  formatParameter,
  formatPercentSigned,
  progressText,
  systemOptimizationPath,
} from '../../utils/systemOptimization';
import { CreateSystemOptimizationModal } from './CreateSystemOptimizationModal';

const PAGE_SIZE = 20;

function outcomeCell(o: SystemOptimizationResponse) {
  if (o.status === 'created' || o.status === 'running') return <Tag color="processing">{progressText(o.progress)}</Tag>;
  const c = o.comparison;
  if (!c) return '—';
  return (
    <Tag color={c.improved ? 'success' : 'default'}>
      {c.improved ? formatPercentSigned(c.relative_improvement_percent) : 'No improvement'}
    </Tag>
  );
}

const columns: ColumnsType<SystemOptimizationResponse> = [
  { title: '优化编号 Optimization ID', dataIndex: 'optimization_id', render: (id: string) => <code>{id}</code> },
  {
    title: '场景 Scenario',
    key: 'scenario',
    render: (_, o) => (
      <>
        {o.scenario_name_zh}
        <div className="muted">{o.scenario_id}</div>
      </>
    ),
  },
  {
    title: '算法 Algorithm',
    key: 'algorithm',
    render: (_, o) => (
      <>
        <code>{o.optimizer_id}</code>
        <div className="muted">v{o.optimizer_version}</div>
      </>
    ),
  },
  { title: '变量 Variable', key: 'var', render: (_, o) => <code>{o.parameter.id}</code> },
  { title: '状态 Status', key: 'status', render: (_, o) => <StatusTag status={o.status} /> },
  {
    title: '基线 → 最优 Baseline → Best',
    key: 'params',
    render: (_, o) =>
      o.comparison
        ? `${formatParameter(o.comparison.baseline_parameters[o.parameter.id])} → ${formatParameter(o.comparison.best_parameters[o.parameter.id])}`
        : '—',
  },
  { title: '网络吞吐率 Δ', key: 'delta', align: 'right', render: (_, o) => outcomeCell(o) },
  { title: '协议 Protocol', key: 'protocol', render: (_, o) => `${o.benchmark_protocol.protocol_id} v${o.benchmark_protocol.version}` },
  { title: '总耗时 Total', key: 'total', align: 'right', render: (_, o) => formatSeconds(o.runtime.total_seconds, 1) },
  { title: '创建时间 Created', dataIndex: 'created_at', render: (v: string) => formatDateTime(v) },
];

function ObjectiveCard({ objective }: { objective: SystemObjectiveView }) {
  return (
    <Card
      title={<span>系统级优化目标 <span className="card-title-en">System Objective</span></span>}
      extra={<Tag color="blue">{objective.id}</Tag>}
      className="fill-height"
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="名称 Name">
          {objective.name_zh} <span className="muted">{objective.name_en} · v{objective.version}</span>
        </Descriptions.Item>
        <Descriptions.Item label="方向 Direction">{objective.direction}</Descriptions.Item>
        <Descriptions.Item label="公式 Formula"><code>{objective.formula}</code></Descriptions.Item>
        <Descriptions.Item label="验收 KPI Acceptance KPI"><Tag>{objective.acceptance_kpi ? 'Yes' : 'No'}</Tag></Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

function ProtocolCard({ protocol }: { protocol: BenchmarkProtocol }) {
  return (
    <Card
      title={<span>评估协议 <span className="card-title-en">Benchmark Protocol</span></span>}
      extra={<Tag color="purple">{protocol.protocol_id} v{protocol.version}</Tag>}
      className="fill-height"
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="时隙 Slots">
          {protocol.simulation_slots} <span className="muted">(warm-up {protocol.warmup_slots})</span>
        </Descriptions.Item>
        <Descriptions.Item label="重复 Repeats">{protocol.num_repeats} · {protocol.aggregation_method}</Descriptions.Item>
        <Descriptions.Item label="公共条件 Common">
          {protocol.common_channel && <Tag>Channel</Tag>}
          {protocol.common_ue_population && <Tag>UE Population</Tag>}
          {protocol.common_traffic && <Tag>Traffic</Tag>}
        </Descriptions.Item>
        <Descriptions.Item label="冻结 Frozen">{protocol.frozen_at}</Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

export function SystemOptimizations() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const algorithms = useAlgorithms();
  const objectives = useSystemObjectives();
  const parameters = useSystemParameters();
  const protocols = useBenchmarkProtocols();
  const runs = useSystemOptimizations(PAGE_SIZE, (page - 1) * PAGE_SIZE);
  const catalog = [objectives, parameters, protocols];
  const catalogError = [algorithms, ...catalog].find((q) => q.isError);
  const algorithmItems = algorithms.data?.items ?? [];
  const catalogReady = algorithmItems.length > 0 && catalog.every((q) => q.data && q.data.length > 0);

  return (
    <>
      <div className="toolbar-right section-bottom">
        <Button type="primary" disabled={!catalogReady} onClick={() => setModalOpen(true)}>
          新建系统级优化 New System Optimization
        </Button>
      </div>
      {catalogError ? (
        <Card className="section-bottom">
          <ErrorState
            error={catalogError.error}
            onRetry={() => [algorithms, ...catalog].forEach((q) => void q.refetch())}
          />
        </Card>
      ) : !catalogReady ? (
        <Card className="section-bottom"><Skeleton active /></Card>
      ) : (
        <Row gutter={[16, 16]} className="section-bottom">
          {objectives.data?.map((o) => (
            <Col key={o.id} xs={24} lg={12}><ObjectiveCard objective={o} /></Col>
          ))}
          {protocols.data?.map((p) => (
            <Col key={p.protocol_id} xs={24} lg={12}><ProtocolCard protocol={p} /></Col>
          ))}
          <Col span={24}>
            <Alert
              type="info"
              showIcon
              title="算法来自 Algorithm Registry：Grid Search 为工程基线，Research Demo Optimizer 为接入验证算法；两者都不是项目学习优化算法。"
            />
          </Col>
        </Row>
      )}
      <Card title={<span>系统级优化实验 <span className="card-title-en">System Optimization Runs</span></span>}>
        {runs.isError ? (
          <ErrorState error={runs.error} onRetry={() => runs.refetch()} />
        ) : (
          <Table
            rowKey="optimization_id"
            size="middle"
            columns={columns}
            dataSource={runs.data?.items ?? []}
            loading={runs.isLoading}
            rowClassName="clickable-row"
            onRow={(o) => ({ onClick: () => navigate(systemOptimizationPath(o.optimization_id)) })}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: runs.data?.total ?? 0,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 个系统级优化 / ${total} runs`,
              onChange: setPage,
            }}
            locale={{
              emptyText: (
                <Empty
                  description={
                    <>
                      <div className="empty-title">暂无系统级优化 / No system optimization runs yet</div>
                      <div className="muted">在冻结评估协议下比较调度参数候选。</div>
                    </>
                  }
                />
              ),
            }}
          />
        )}
      </Card>
      {modalOpen && catalogReady && (
        <CreateSystemOptimizationModal
          open={modalOpen}
          algorithms={algorithmItems}
          objectives={objectives.data ?? []}
          parameters={parameters.data ?? []}
          protocols={protocols.data ?? []}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  );
}
