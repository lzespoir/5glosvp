import { ArrowLeftOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Row, Skeleton, Space } from 'antd';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { resolveApiUrl } from '../../api/client';
import { useKpiDefinitions, useSystemExperiment } from '../../api/system';
import { ErrorState } from '../../components/ErrorState';
import { NetworkView } from '../../components/NetworkView';
import { PageHeader } from '../../components/PageHeader';
import { StatusTag } from '../../components/StatusTag';
import { SystemModelBadge } from '../../components/SystemModelBadge';
import { UeThroughputChart } from '../../components/UeThroughputChart';
import { formatDateTime, formatSeconds } from '../../utils/format';
import { AVG_UE_THROUGHPUT, findKpi, modelMeta, P5_EDGE_NOTE, P5_UE_THROUGHPUT, SCIENTIFIC_BOUNDARY } from '../../utils/system';
import { KpiCards } from './KpiCards';
import { KpiDetailModal } from './KpiDetailModal';
import { SystemProvenance } from './SystemProvenance';
import { UeDrawer } from './UeDrawer';
import { UeTable } from './UeTable';

function sectionTitle(zh: string, en: string) {
  return (
    <span>
      {zh} <span className="card-title-en">{en}</span>
    </span>
  );
}

export function SystemExperimentDetailPage() {
  const { experimentId = '' } = useParams();
  const navigate = useNavigate();
  const query = useSystemExperiment(experimentId);
  const definitions = useKpiDefinitions();
  const [kpiOpen, setKpiOpen] = useState<string | null>(null);
  const [ueOpen, setUeOpen] = useState<string | null>(null);
  const exp = query.data;
  const result = exp?.result ?? null;

  const baseStations = useMemo(
    () => (result ? result.cells.map((c) => ({ id: `${c.bs_id} / ${c.cell_id}`, position: c.position })) : []),
    [result],
  );
  const ues = useMemo(
    () => (result ? result.ue_results.map((u) => ({ id: u.ue_id, position: u.position, throughputMbps: u.throughput_mbps })) : []),
    [result],
  );
  const onSelectUe = useCallback((id: string) => setUeOpen(id), []);

  const back = (
    <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/system')}>
      返回系统级仿真
    </Button>
  );

  if (query.isLoading) {
    return (
      <>
        <PageHeader titleZh="系统级仿真结果" titleEn="System Simulation Result" extra={back} />
        <Skeleton active paragraph={{ rows: 12 }} />
      </>
    );
  }
  if (query.isError || !exp) {
    return (
      <>
        <PageHeader titleZh="系统级仿真结果" titleEn="System Simulation Result" extra={back} />
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      </>
    );
  }

  const meta = modelMeta(exp.backend.model_type);
  const selectedUe = result?.ue_results.find((u) => u.ue_id === ueOpen);
  const summary = exp.artifacts.find((a) => a.name === 'system_summary.png');

  return (
    <>
      <PageHeader
        titleZh="系统级仿真结果"
        titleEn="System Simulation Result"
        extra={back}
        subtitle={
          <Space wrap size={[16, 4]} className="experiment-meta">
            <code className="experiment-meta__id">{exp.experiment_id}</code>
            <StatusTag status={exp.status} showEn />
            <SystemModelBadge modelType={exp.backend.model_type} />
            <span>后端 Backend：{exp.backend.id}{exp.backend.version ? ` ${exp.backend.version}` : ''}</span>
            <span>场景 Scenario：{exp.scenario.name_zh}</span>
            <span>种子 Seed：{exp.seed}</span>
            <span>运行时间 Runtime：{formatSeconds(result?.runtime.total_seconds ?? null, 1)}</span>
            <span>数据来源 Source：{exp.backend.source_type ?? '—'}</span>
          </Space>
        }
      />

      <Alert
        type="warning"
        showIcon
        className={`section-bottom boundary-banner ${meta.className}`}
        title={SCIENTIFIC_BOUNDARY}
        description={<span>{meta.label} · {meta.labelZh} · Measured: No · Huawei Data: No · Acceptance Evidence: No</span>}
        data-testid="scientific-boundary"
      />
      {exp.status === 'failed' && (
        <Alert
          type="error"
          showIcon
          className="section-bottom"
          title="系统级仿真失败 System Simulation Failed"
          description={exp.error ? <span><code>{exp.error.code}</code> · {exp.error.message}</span> : '后端未返回错误详情 / No error detail'}
        />
      )}
      {(exp.status === 'created' || exp.status === 'running') && (
        <Alert type="info" showIcon className="section-bottom" title="系统级仿真正在执行，页面将自动刷新。Simulation in progress." />
      )}

      {result && (
        <>
          <KpiCards kpis={exp.kpis} ueCount={result.ue_results.length} onOpen={setKpiOpen} />
          <div className="muted section-note">{P5_EDGE_NOTE}</div>

          <Row gutter={[16, 16]} className="section">
            <Col xs={24} xl={12}>
              <Card size="small" title={sectionTitle('UE 吞吐率分布', 'UE Throughput Distribution')} className="fill-height">
                <UeThroughputChart
                  ues={result.ue_results}
                  averageMbps={findKpi(exp.kpis, AVG_UE_THROUGHPUT)?.value ?? null}
                  p5Mbps={findKpi(exp.kpis, P5_UE_THROUGHPUT)?.value ?? null}
                />
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card size="small" title={sectionTitle('网络视图', 'Network View')} className="fill-height">
                <NetworkView baseStations={baseStations} ues={ues} onSelectUe={onSelectUe} height={320} />
                <div className="muted">UE ● 颜色为吞吐率；场景坐标 [m]，无地图底图。点击 UE 查看计算链。</div>
              </Card>
            </Col>
          </Row>

          <Card size="small" className="section" title={sectionTitle('UE 结果', 'Per-UE Results')}>
            <UeTable ues={result.ue_results} onSelect={setUeOpen} />
            <div className="muted">点击行查看计算链 · Click a row for the computation chain</div>
          </Card>
        </>
      )}

      <Row gutter={[16, 16]} className="section">
        <Col xs={24} lg={12}>
          <Card size="small" title={sectionTitle('数据来源与高级信息', 'Provenance / Advanced')} className="fill-height">
            <SystemProvenance experiment={exp} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={sectionTitle('运行耗时与产物', 'Runtime & Artifacts')} className="fill-height">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="传播 Propagation (RT)">{formatSeconds(result?.runtime.propagation_seconds ?? null, 2)}</Descriptions.Item>
              <Descriptions.Item label="系统级 System (SYS)">{formatSeconds(result?.runtime.system_seconds ?? null, 2)}</Descriptions.Item>
              <Descriptions.Item label="总计 Total">{formatSeconds(result?.runtime.total_seconds ?? null, 2)}</Descriptions.Item>
              <Descriptions.Item label="创建 Created">{formatDateTime(exp.created_at)}</Descriptions.Item>
            </Descriptions>
            <div className="muted">平台运行耗时，不是验收指标。Platform runtime, not an acceptance KPI.</div>
            <ul className="plain-list section">
              {exp.artifacts.map((a) => (
                <li key={a.name}>
                  <a href={resolveApiUrl(a.url)} target="_blank" rel="noreferrer"><code>{a.name}</code></a>
                  {a.description && <span className="muted"> · {a.description}</span>}
                </li>
              ))}
            </ul>
            {summary && (
              <img className="system-summary-img" src={resolveApiUrl(summary.url)} alt={`System summary of ${exp.experiment_id}`} />
            )}
          </Card>
        </Col>
      </Row>

      {kpiOpen && (
        <KpiDetailModal
          metricId={kpiOpen}
          kpi={findKpi(exp.kpis, kpiOpen)}
          definition={definitions.data?.find((d) => d.id === kpiOpen)}
          onClose={() => setKpiOpen(null)}
        />
      )}
      {selectedUe && result && (
        <UeDrawer ue={selectedUe} result={result} modelType={exp.backend.model_type} onClose={() => setUeOpen(null)} />
      )}
    </>
  );
}
