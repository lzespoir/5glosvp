import {
  ArrowRightOutlined,
  AuditOutlined,
  ClusterOutlined,
  EnvironmentOutlined,
  FunctionOutlined,
} from '@ant-design/icons';
import { Badge, Button, Card, Col, Descriptions, Empty, Row, Skeleton, Space, Statistic, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useBackends } from '../../api/backends';
import { useExperiments } from '../../api/experiments';
import { useOptimizations } from '../../api/optimizations';
import { useScenarios } from '../../api/scenarios';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import { findRadioMap, RadioMap } from '../../components/RadioMap';
import { RuntimeChart } from '../../components/RuntimeChart';
import { StatusTag } from '../../components/StatusTag';
import type { ExperimentResponse } from '../../types/experiment';
import { EMPTY, formatDateTime, formatSeconds } from '../../utils/format';

const RECENT_LIMIT = 20;

const QUICK_START: { titleZh: string; titleEn: string; desc: string; to: string | null; icon: ReactNode }[] = [
  { titleZh: '运行传播仿真', titleEn: 'Run Propagation Simulation', desc: 'Sionna RT 无线电地图', to: '/scenarios', icon: <EnvironmentOutlined /> },
  { titleZh: '运行系统仿真', titleEn: 'Run System Simulation', desc: '多 UE 下行吞吐率与网络 KPI', to: '/system', icon: <ClusterOutlined /> },
  { titleZh: '运行参数优化', titleEn: 'Run Parameter Optimization', desc: '传播层目标函数网格搜索', to: '/optimizations', icon: <FunctionOutlined /> },
  { titleZh: '验收验证', titleEn: 'Acceptance Validation', desc: '尚未开放', to: null, icon: <AuditOutlined /> },
];

export const recentColumns: ColumnsType<ExperimentResponse> = [
  { title: '实验 Experiment', dataIndex: 'experiment_id', render: (id: string) => <code>{id}</code> },
  { title: '场景 Scenario', key: 'scenario', render: (_, e) => e.scenario.name_zh },
  { title: '后端 Backend', key: 'backend', render: (_, e) => e.backend.id },
  { title: '状态 Status', dataIndex: 'status', render: (_, e) => <StatusTag status={e.status} /> },
  { title: '仿真时间 Simulation', key: 'sim', render: (_, e) => formatSeconds(e.runtime.simulation_seconds) },
  { title: '创建时间 Created', dataIndex: 'created_at', render: (v: string) => formatDateTime(v) },
];

function KpiCard({ titleZh, titleEn, loading, children }: {
  titleZh: string;
  titleEn: string;
  loading: boolean;
  children: ReactNode;
}) {
  return (
    <Card size="small" className="kpi-card">
      <div className="kpi-card__title">
        {titleZh} <span className="muted">{titleEn}</span>
      </div>
      {loading ? <Skeleton active paragraph={{ rows: 1 }} title={false} /> : children}
    </Card>
  );
}

export function OverviewPage() {
  const navigate = useNavigate();
  const backends = useBackends();
  const scenarios = useScenarios();
  const experiments = useExperiments(RECENT_LIMIT, 0);
  const optimizations = useOptimizations(1, 0);

  const items = experiments.data?.items ?? [];
  const latest = items[0];
  const latestSucceeded = items.find((e) => e.status === 'succeeded' && findRadioMap(e));

  return (
    <>
      <PageHeader
        titleZh="平台概览"
        titleEn="Platform Overview"
        subtitle={
          <>
            面向5G网络学习优化算法的仿真、实验与验证平台
            <br />
            <span className="muted">Simulation, experimentation and validation for 5G network learning optimization</span>
          </>
        }
      />

      <Card
        size="small"
        className="section-bottom"
        title={<span>快速开始 <span className="card-title-en">Quick Start</span></span>}
        data-testid="quick-start"
      >
        <Row gutter={[12, 12]}>
          {QUICK_START.map(({ to, ...q }) => (
            <Col xs={24} sm={12} xl={6} key={q.titleEn}>
              <Card
                size="small"
                hoverable={to !== null}
                className={`quick-start__item${to ? '' : ' quick-start__item--disabled'}`}
                onClick={to ? () => navigate(to) : undefined}
              >
                <Space align="start">
                  <span className="quick-start__icon">{q.icon}</span>
                  <span>
                    <div className="quick-start__title">
                      {q.titleZh} {!to && <Tag>Coming Soon</Tag>}
                    </div>
                    <div className="muted">{q.titleEn}</div>
                    <div className="muted quick-start__desc">{q.desc}</div>
                  </span>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard titleZh="仿真后端" titleEn="Simulation Backend" loading={backends.isLoading}>
            {backends.isError ? (
              <Badge status="error" text="API 不可达 / Unreachable" />
            ) : (
              (backends.data ?? []).map((b) => (
                <div key={b.id} className="kpi-card__backend">
                  <span className="kpi-card__value kpi-card__value--sm">{b.name_zh}</span>
                  <Badge status={b.available ? 'success' : 'error'} text={b.available ? '就绪 Ready' : '不可用 Unavailable'} />
                  {b.version && <span className="muted"> · v{b.version}</span>}
                </div>
              ))
            )}
          </KpiCard>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard titleZh="场景" titleEn="Scenarios" loading={scenarios.isLoading}>
            <Statistic value={scenarios.data?.length ?? EMPTY} suffix={<span className="muted">Scenarios</span>} />
          </KpiCard>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard titleZh="实验" titleEn="Experiments" loading={experiments.isLoading}>
            <Statistic value={experiments.data?.total ?? EMPTY} suffix={<span className="muted">Experiments</span>} />
          </KpiCard>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard titleZh="优化实验" titleEn="Optimization Runs" loading={optimizations.isLoading}>
            {optimizations.isError ? (
              <Badge status="error" text="不可用 / Unavailable" />
            ) : (
              <Link to="/optimizations" className="kpi-card__link">
                <Statistic value={optimizations.data?.total ?? EMPTY} suffix={<span className="muted">Runs</span>} />
              </Link>
            )}
          </KpiCard>
        </Col>
      </Row>

      {experiments.isError ? (
        <ErrorState error={experiments.error} onRetry={() => experiments.refetch()} />
      ) : !experiments.isLoading && items.length === 0 ? (
        <Card className="section">
          <Empty
            description={
              <>
                <div className="empty-title">暂无实验 / No experiments yet</div>
                <div className="muted">选择一个仿真场景，开始第一次 Sionna RT 实验。</div>
              </>
            }
          >
            <Button type="primary" onClick={() => navigate('/scenarios')}>
              前往场景中心 Go to Scenario Center
            </Button>
          </Empty>
        </Card>
      ) : (
        <Row gutter={[16, 16]} className="section">
          <Col xs={24} xxl={14}>
            <Card
              title={<span>最新无线电地图 <span className="card-title-en">Latest Radio Map</span></span>}
              extra={latestSucceeded && <Link to={`/experiments/${latestSucceeded.experiment_id}`}>查看实验详情 →</Link>}
            >
              {experiments.isLoading ? (
                <Skeleton.Image active className="radio-map__skeleton" />
              ) : latestSucceeded ? (
                <RadioMap experiment={latestSucceeded} maxHeight="52vh" />
              ) : (
                <Empty description="暂无成功实验 / No succeeded experiment" />
              )}
            </Card>
          </Col>
          <Col xs={24} xxl={10}>
            <Card
              title={<span>最近实验 <span className="card-title-en">Latest Experiment</span></span>}
              loading={experiments.isLoading}
              extra={
                latest && (
                  <Link to={`/experiments/${latest.experiment_id}`}>
                    查看实验详情 View Experiment <ArrowRightOutlined />
                  </Link>
                )
              }
            >
              {latest && (
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Experiment ID"><code>{latest.experiment_id}</code></Descriptions.Item>
                  <Descriptions.Item label="场景 Scenario">{latest.scenario.name_zh}</Descriptions.Item>
                  <Descriptions.Item label="后端 Backend">
                    {latest.backend.id}{latest.backend.version ? ` ${latest.backend.version}` : ''}
                  </Descriptions.Item>
                  <Descriptions.Item label="状态 Status"><StatusTag status={latest.status} showEn /></Descriptions.Item>
                  <Descriptions.Item label="创建时间 Created">{formatDateTime(latest.created_at)}</Descriptions.Item>
                  <Descriptions.Item label="运行时间 Runtime">{formatSeconds(latest.runtime.total_seconds)}</Descriptions.Item>
                </Descriptions>
              )}
            </Card>
            <Card
              className="section"
              title={<span>最近实验运行耗时 <span className="card-title-en">Recent Experiment Runtime</span></span>}
              loading={experiments.isLoading}
            >
              <RuntimeChart experiments={items.slice(0, 10)} height={240} />
            </Card>
          </Col>
          <Col span={24}>
            <Card
              title={<span>最近实验 <span className="card-title-en">Recent Experiments</span></span>}
              extra={<Link to="/experiments">全部实验 →</Link>}
            >
              <Table
                rowKey="experiment_id"
                size="small"
                columns={recentColumns}
                dataSource={items.slice(0, 5)}
                loading={experiments.isLoading}
                pagination={false}
                rowClassName="clickable-row"
                onRow={(e) => ({ onClick: () => navigate(`/experiments/${e.experiment_id}`) })}
              />
            </Card>
          </Col>
        </Row>
      )}
    </>
  );
}
