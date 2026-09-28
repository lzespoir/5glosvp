import { PlayCircleOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Skeleton, Space, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useSystemBackends, useSystemExperiments, useSystemScenario, useSystemScenarios } from '../../api/system';
import { ErrorState } from '../../components/ErrorState';
import { NetworkView } from '../../components/NetworkView';
import { PageHeader } from '../../components/PageHeader';
import { StatusTag } from '../../components/StatusTag';
import { SystemModelBadge } from '../../components/SystemModelBadge';
import type { SystemBackendView, SystemExperimentResponse, SystemScenarioSummary } from '../../types/system';
import { formatDateTime, formatHz, formatSeconds, formatValue } from '../../utils/format';
import { findKpi, NETWORK_THROUGHPUT, SCIENTIFIC_BOUNDARY, systemPurposeMeta } from '../../utils/system';
import { RunSystemModal } from './RunSystemModal';

const RECENT_LIMIT = 10;

export const systemExperimentColumns: ColumnsType<SystemExperimentResponse> = [
  { title: '实验编号 Experiment ID', dataIndex: 'experiment_id', render: (id: string) => <code>{id}</code> },
  {
    title: '场景 Scenario',
    key: 'scenario',
    render: (_, e) => (
      <>
        {e.scenario.name_zh}
        <div className="muted">{e.scenario.scenario_id}</div>
      </>
    ),
  },
  { title: '后端 Backend', key: 'backend', render: (_, e) => `${e.backend.id}${e.backend.version ? ` ${e.backend.version}` : ''}` },
  { title: '来源 Source', key: 'source', render: (_, e) => <SystemModelBadge modelType={e.backend.model_type} /> },
  { title: '状态 Status', key: 'status', render: (_, e) => <StatusTag status={e.status} /> },
  {
    title: '用途 Purpose',
    key: 'purpose',
    render: (_, e) => {
      const p = systemPurposeMeta(e.purpose);
      return p ? <Tag color="purple">{p.en}</Tag> : <span className="muted">Standalone</span>;
    },
  },
  { title: 'UE', key: 'ue', align: 'right', render: (_, e) => e.result?.ue_results.length ?? '—' },
  {
    title: '网络吞吐率 Network',
    key: 'network',
    align: 'right',
    render: (_, e) => formatValue(findKpi(e.kpis, NETWORK_THROUGHPUT)?.value, 'Mbps', 2),
  },
  { title: '总耗时 Total', key: 'total', align: 'right', render: (_, e) => formatSeconds(e.result?.runtime.total_seconds ?? null, 1) },
  { title: '创建时间 Created', dataIndex: 'created_at', render: (v: string) => formatDateTime(v) },
];

function ScenarioPanel({ scenario, backend, onRun }: {
  scenario: SystemScenarioSummary;
  backend: SystemBackendView | undefined;
  onRun: () => void;
}) {
  const detail = useSystemScenario(scenario.scenario_id);
  const s = detail.data?.scenario;
  const baseStations = useMemo(
    () => (s ? s.cells.map((c) => ({ id: c.cell_id, position: c.position ?? s.base_stations.find((b) => b.bs_id === c.bs_id)?.position ?? [0, 0, 0] })) : []),
    [s],
  );
  const ues = useMemo(() => (s ? s.ues.map((u) => ({ id: u.ue_id, position: u.position })) : []), [s]);
  const area = s?.ue_generator ? { center: s.ue_generator.area_center, size: s.ue_generator.area_size } : null;

  return (
    <Card
      className="system-scenario"
      title={
        <span>
          {scenario.name_zh} <span className="card-title-en">{scenario.name_en}</span>
        </span>
      }
      extra={
        <Button type="primary" icon={<PlayCircleOutlined />} onClick={onRun} disabled={!backend?.available} data-testid="run-system">
          运行系统仿真 Run
        </Button>
      }
    >
      <Row gutter={[24, 16]}>
        <Col xs={24} xl={11}>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="场景名称 Scenario">
              {scenario.name_zh}
              <div className="muted">{scenario.scenario_id}</div>
            </Descriptions.Item>
            <Descriptions.Item label="基站 / 小区 BS / Cell">
              {scenario.bs_count} / {scenario.cell_count}
            </Descriptions.Item>
            <Descriptions.Item label="UE 数量 UE Count">
              {scenario.ue_count}
              {scenario.ue_placement.startsWith('generator') && (
                <span className="muted"> · 按种子程序生成 Seeded generator</span>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="频率 Frequency">{formatHz(scenario.carrier_frequency_hz)}</Descriptions.Item>
            <Descriptions.Item label="带宽 Bandwidth">{formatHz(scenario.bandwidth_hz)}</Descriptions.Item>
            <Descriptions.Item label="业务模型 Traffic">
              {scenario.traffic_model === 'full_buffer' ? '满缓冲 Full Buffer' : scenario.traffic_model} · 下行 Downlink{' '}
              <Tag>[A]</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="仿真后端 Backend">
              <Space size={4} wrap>
                <span>{backend?.name_zh ?? scenario.backend}</span>
                <SystemModelBadge modelType={backend?.model_type} />
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="随机种子 Seed">{scenario.seed}</Descriptions.Item>
            <Descriptions.Item label="数据来源 Data Source">{scenario.data_source}</Descriptions.Item>
          </Descriptions>
          {scenario.description && <div className="muted section">{scenario.description}</div>}
        </Col>
        <Col xs={24} xl={13}>
          <div className="section-label">
            网络视图 Network View <span className="muted">· BS ▲ · 场景坐标 [m]，无地图底图</span>
          </div>
          {detail.isLoading ? (
            <Skeleton.Image active />
          ) : (
            <NetworkView baseStations={baseStations} ues={ues} area={area} height={320} />
          )}
          {area && (
            <div className="muted">UE 位置在运行时由种子生成器确定（仅保留存在传播路径的位置），结果页显示实际位置。</div>
          )}
        </Col>
      </Row>
    </Card>
  );
}

export function SystemPage() {
  const navigate = useNavigate();
  const backends = useSystemBackends();
  const scenarios = useSystemScenarios();
  const experiments = useSystemExperiments(RECENT_LIMIT, 0);
  const [running, setRunning] = useState<SystemScenarioSummary | null>(null);

  const backendFor = (s: SystemScenarioSummary) =>
    (backends.data ?? []).find((b) => b.id === s.backend && b.capabilities.includes('throughput'));

  return (
    <>
      <PageHeader
        titleZh="系统级仿真"
        titleEn="System Simulation"
        subtitle="多用户下行系统仿真：传播 → PHY → 调度 → UE 吞吐率 → 网络 KPI · Multi-UE downlink system-level simulation"
      />
      <Alert type="warning" showIcon className="section-bottom" title={SCIENTIFIC_BOUNDARY} data-testid="scientific-boundary" />

      {scenarios.isError ? (
        <ErrorState error={scenarios.error} onRetry={() => scenarios.refetch()} />
      ) : scenarios.isLoading || backends.isLoading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (scenarios.data ?? []).length === 0 ? (
        <Card><Empty description="暂无系统级场景 / No system scenarios" /></Card>
      ) : (
        (scenarios.data ?? []).map((s) => (
          <ScenarioPanel key={s.scenario_id} scenario={s} backend={backendFor(s)} onRun={() => setRunning(s)} />
        ))
      )}

      <Card
        className="section"
        title={<span>最近系统级实验 <span className="card-title-en">Recent System Experiments</span></span>}
        extra={<Button type="link" onClick={() => navigate('/experiments?type=system')}>全部 →</Button>}
      >
        {experiments.isError ? (
          <ErrorState error={experiments.error} onRetry={() => experiments.refetch()} />
        ) : (
          <Table
            rowKey="experiment_id"
            size="small"
            columns={systemExperimentColumns}
            dataSource={experiments.data?.items ?? []}
            loading={experiments.isLoading}
            pagination={false}
            rowClassName="clickable-row"
            onRow={(e) => ({ onClick: () => navigate(`/system/experiments/${e.experiment_id}`) })}
            locale={{ emptyText: '暂无系统级实验 / No system experiments yet' }}
          />
        )}
      </Card>

      {running && (
        <RunSystemModal open scenario={running} backend={backendFor(running)} onClose={() => setRunning(null)} />
      )}
    </>
  );
}
