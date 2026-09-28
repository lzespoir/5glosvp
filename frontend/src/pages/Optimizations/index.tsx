import { Alert, Button, Card, Col, Descriptions, Empty, Row, Segmented, Skeleton, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useObjectives, useOptimizations, useOptimizers } from '../../api/optimizations';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import { StatusTag } from '../../components/StatusTag';
import type { ObjectiveView, OptimizationResponse, OptimizerView } from '../../types/optimization';
import { formatDateTime, formatSeconds } from '../../utils/format';
import { formatPower, formatSigned, improvementMeta, TX_POWER } from '../../utils/optimization';
import { CreateOptimizationModal } from './CreateOptimizationModal';
import { SystemOptimizations } from './SystemOptimizations';

export const PAGE_SIZE = 20;

export const OPTIMIZER_NOTE = '用于验证平台优化闭环，不代表项目最终学习优化算法。';

const columns: ColumnsType<OptimizationResponse> = [
  { title: '优化编号 Optimization ID', dataIndex: 'optimization_id', render: (id: string) => <code>{id}</code> },
  {
    title: '场景 Scenario',
    key: 'scenario',
    render: (_, o) => (
      <>
        {o.scenario.name_zh}
        <div className="muted">{o.scenario.scenario_id}</div>
      </>
    ),
  },
  { title: '优化器 Optimizer', key: 'optimizer', render: (_, o) => o.optimizer.name_en ?? o.optimizer.id },
  { title: '状态 Status', dataIndex: 'status', render: (_, o) => <StatusTag status={o.status} /> },
  {
    title: '参数 TX Power',
    key: 'params',
    render: (_, o) =>
      o.comparison
        ? `${formatPower(o.comparison.baseline_parameters[TX_POWER])} → ${formatPower(o.comparison.optimized_parameters[TX_POWER])}`
        : '—',
  },
  {
    title: '目标改善 ΔJ',
    key: 'improvement',
    align: 'right',
    render: (_, o) =>
      o.comparison && o.improvement_status ? (
        <Tag color={improvementMeta(o.improvement_status).color}>{formatSigned(o.comparison.absolute_improvement)}</Tag>
      ) : (
        '—'
      ),
  },
  { title: '候选数 Candidates', key: 'n', align: 'right', render: (_, o) => o.candidates.length },
  { title: '总耗时 Total', key: 'total', align: 'right', render: (_, o) => formatSeconds(o.runtime.total_seconds, 1) },
  { title: '创建时间 Created', dataIndex: 'created_at', render: (v: string) => formatDateTime(v) },
];

function OptimizerCard({ optimizer }: { optimizer: OptimizerView }) {
  return (
    <Card
      title={<span>{optimizer.name_zh} <span className="card-title-en">{optimizer.name_en}</span></span>}
      extra={<Tag color={optimizer.available ? 'green' : 'default'}>{optimizer.available ? '可用 Available' : '不可用'}</Tag>}
      className="fill-height"
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="类别 Category">
          工程基线优化器 <span className="muted">Engineering Baseline ({optimizer.category})</span>
        </Descriptions.Item>
        <Descriptions.Item label="Learning Algorithm">
          <Tag>{optimizer.learning_algorithm ? 'Yes' : 'No'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="参数 Parameters">
          {optimizer.supported_parameters.map((p) => `${p.name_zh} ${p.name_en} (${p.unit})`).join(', ')}
        </Descriptions.Item>
        <Descriptions.Item label="推荐搜索空间">
          {(optimizer.recommended_parameter_space[TX_POWER] ?? []).join(' / ')} dBm{' '}
          <Tag color="gold">[A] Demo</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="候选上限 Max">{optimizer.max_candidates}</Descriptions.Item>
      </Descriptions>
      <Alert type="info" showIcon className="section" title={OPTIMIZER_NOTE} />
    </Card>
  );
}

function ObjectiveCard({ objective }: { objective: ObjectiveView }) {
  return (
    <Card
      title={<span>优化目标 <span className="card-title-en">Objective</span></span>}
      extra={<Tag color="blue">{objective.id}</Tag>}
      className="fill-height"
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="名称 Name">
          {objective.name_zh} <span className="muted">{objective.name_en} · v{objective.version}</span>
        </Descriptions.Item>
        <Descriptions.Item label="方向 Direction">{objective.direction}</Descriptions.Item>
        <Descriptions.Item label="公式 Formula">
          <code>{objective.formula}</code>
        </Descriptions.Item>
        {Object.entries(objective.default_params).map(([k, v]) => (
          <Descriptions.Item key={k} label={k}>
            {v} <Tag color="gold">[A] Assumption</Tag>
          </Descriptions.Item>
        ))}
      </Descriptions>
      <div className="muted section">{objective.description_zh}</div>
    </Card>
  );
}

export type OptimizationType = 'propagation' | 'system';

export function optimizationType(value: string | null): OptimizationType {
  return value === 'system' ? 'system' : 'propagation';
}

export function OptimizationsPage() {
  const [params, setParams] = useSearchParams();
  const type = optimizationType(params.get('type'));
  return (
    <>
      <PageHeader
        titleZh="优化中心"
        titleEn="Optimization Center"
        subtitle="参数优化闭环 · Parameter optimization loop over real simulations"
        extra={
          <Segmented<OptimizationType>
            aria-label="Optimization type"
            value={type}
            onChange={(v) => setParams(v === 'system' ? { type: v } : {})}
            options={[
              { value: 'propagation', label: '传播层优化 Propagation' },
              { value: 'system', label: '系统级优化 System' },
            ]}
          />
        }
      />
      {type === 'system' ? <SystemOptimizations /> : <PropagationOptimizations />}
    </>
  );
}

function PropagationOptimizations() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const optimizers = useOptimizers();
  const objectives = useObjectives();
  const runs = useOptimizations(PAGE_SIZE, (page - 1) * PAGE_SIZE);
  const catalogReady = !!optimizers.data && !!objectives.data && optimizers.data.length > 0;

  return (
    <>
      <div className="toolbar-right section-bottom">
        <Button type="primary" disabled={!catalogReady} onClick={() => setModalOpen(true)}>
          新建优化实验 New Optimization Run
        </Button>
      </div>
      {optimizers.isError || objectives.isError ? (
        <Card className="section-bottom">
          <ErrorState
            error={optimizers.error ?? objectives.error}
            onRetry={() => {
              void optimizers.refetch();
              void objectives.refetch();
            }}
          />
        </Card>
      ) : !catalogReady ? (
        <Card className="section-bottom"><Skeleton active /></Card>
      ) : (
        <Row gutter={[16, 16]} className="section-bottom">
          {optimizers.data?.map((o) => (
            <Col key={o.id} xs={24} lg={12}><OptimizerCard optimizer={o} /></Col>
          ))}
          {objectives.data?.map((o) => (
            <Col key={o.id} xs={24} lg={12}><ObjectiveCard objective={o} /></Col>
          ))}
        </Row>
      )}
      <Card title={<span>优化实验 <span className="card-title-en">Optimization Runs</span></span>}>
        {runs.isError ? (
          <ErrorState error={runs.error} onRetry={() => runs.refetch()} />
        ) : (
          <Table
            rowKey="optimization_id"
            size="middle"
            columns={columns}
            dataSource={runs.data?.items ?? []}
            loading={runs.isLoading || runs.isFetching}
            rowClassName="clickable-row"
            onRow={(o) => ({ onClick: () => navigate(`/optimizations/${o.optimization_id}`) })}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: runs.data?.total ?? 0,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 个优化实验 / ${total} runs`,
              onChange: setPage,
            }}
            locale={{
              emptyText: (
                <Empty
                  description={
                    <>
                      <div className="empty-title">暂无优化实验 / No optimization runs yet</div>
                      <div className="muted">新建一次网格搜索，验证参数优化闭环。</div>
                    </>
                  }
                />
              ),
            }}
          />
        )}
      </Card>
      {modalOpen && catalogReady && (
        <CreateOptimizationModal
          open={modalOpen}
          optimizers={optimizers.data ?? []}
          objectives={objectives.data ?? []}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  );
}