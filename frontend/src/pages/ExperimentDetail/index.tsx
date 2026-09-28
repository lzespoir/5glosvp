import { ArrowLeftOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Row, Skeleton, Space, Statistic, Tag, Typography } from 'antd';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useExperiment } from '../../api/experiments';
import { ArtifactsPanel } from '../../components/ArtifactsPanel';
import { EmptyMetric } from '../../components/EmptyMetric';
import { ErrorState } from '../../components/ErrorState';
import { MetricCard } from '../../components/MetricCard';
import { PageHeader } from '../../components/PageHeader';
import { ProvenancePanel } from '../../components/ProvenancePanel';
import { RadioMap } from '../../components/RadioMap';
import { RuntimePanel } from '../../components/RuntimePanel';
import { StatusTag } from '../../components/StatusTag';
import { StatusTimeline } from '../../components/StatusTimeline';
import type { ExperimentResponse, LayerStatistics } from '../../types/experiment';
import { formatDateTime, formatPercent } from '../../utils/format';
import { purposeMeta } from '../../utils/optimization';
import { isActiveStatus, isExperimentFailed, isLayerStatistics, orderedLayers } from '../../utils/status';

function sectionTitle(zh: string, en: string) {
  return (
    <span>
      {zh} <span className="card-title-en">{en}</span>
    </span>
  );
}

/** Radio Map 覆盖比例：仅指 Radio Map 中有有效信号的格点比例，不是网络覆盖率或验收覆盖率。 */
function CoverageCard({ stats }: { stats: LayerStatistics }) {
  return (
    <Card size="small" className="metric-card">
      <div className="metric-card__label">
        <span className="metric-card__label-en">Radio Map Coverage</span>
        <span className="metric-card__label-zh">无线电地图覆盖比例</span>
      </div>
      <Statistic title="有效格点占比 Covered ratio" value={formatPercent(stats.coverage_ratio)} />
      <Typography.Text type="secondary" className="metric-card__range">
        {stats.num_covered_cells} / {stats.num_cells} cells · 非网络覆盖率
      </Typography.Text>
    </Card>
  );
}

function MetricsSection({ experiment }: { experiment: ExperimentResponse }) {
  const metrics = experiment.metrics ?? {};
  const layers = orderedLayers(metrics.radio_map_layers);
  const primary = isLayerStatistics(metrics.radio_map) ? metrics.radio_map : layers[0];
  const cards = layers.length > 0 ? layers : primary ? [primary] : [];

  if (cards.length === 0) {
    return (
      <Card size="small">
        <Typography.Text type="secondary">
          {isExperimentFailed(experiment) ? '实验失败，未产生仿真指标。' : '暂无仿真指标。'} No simulation metrics.
        </Typography.Text>
      </Card>
    );
  }

  return (
    <Row gutter={[12, 12]}>
      {cards.map((s) => (
        <Col key={s.metric} xs={24} sm={12}>
          <MetricCard stats={s} primary={s.metric === primary?.metric} />
        </Col>
      ))}
      {primary && (
        <Col xs={24} sm={12}>
          <CoverageCard stats={primary} />
        </Col>
      )}
    </Row>
  );
}

function SystemKpiSection() {
  return (
    <Card title={sectionTitle('系统级 KPI', 'System-level KPI')} className="section" size="small">
      <Row gutter={[12, 12]}>
        <Col xs={24} md={8}>
          <EmptyMetric
            titleZh="网络吞吐量"
            titleEn="Network Throughput"
            reasonZh="尚未接入系统级模型"
            reasonEn="System-level model not connected"
          />
        </Col>
        <Col xs={24} md={8}>
          <EmptyMetric
            titleZh="边缘用户速率"
            titleEn="Edge User Rate"
            reasonZh="验收口径待冻结"
            reasonEn="Acceptance definition TBD"
          />
        </Col>
        <Col xs={24} md={8}>
          <EmptyMetric
            titleZh="参考信号接收功率"
            titleEn="RSRP"
            reasonZh="当前 Radio Map 提供 RSS，不等同于 RSRP"
            reasonEn="Radio Map provides RSS, which is not RSRP"
          />
        </Col>
      </Row>
    </Card>
  );
}

export function ExperimentDetailPage() {
  const { experimentId = '' } = useParams();
  const navigate = useNavigate();
  const query = useExperiment(experimentId);
  const exp = query.data;

  const back = (
    <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/experiments')}>
      返回实验中心
    </Button>
  );

  if (query.isLoading) {
    return (
      <>
        <PageHeader titleZh="实验详情" titleEn="Experiment Detail" extra={back} />
        <Row gutter={16}>
          <Col xs={24} xl={14}><Skeleton.Image active className="radio-map__skeleton" /></Col>
          <Col xs={24} xl={10}><Skeleton active paragraph={{ rows: 8 }} /></Col>
        </Row>
      </>
    );
  }

  if (query.isError || !exp) {
    return (
      <>
        <PageHeader titleZh="实验详情" titleEn="Experiment Detail" extra={back} />
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      </>
    );
  }

  const failed = isExperimentFailed(exp);
  const purpose = purposeMeta(exp.purpose ?? 'manual');

  return (
    <>
      <PageHeader
        titleZh="实验详情"
        titleEn="Experiment Detail"
        extra={back}
        subtitle={
          <Space wrap size={[16, 4]} className="experiment-meta">
            <code className="experiment-meta__id">{exp.experiment_id}</code>
            <StatusTag status={exp.status} showEn />
            {purpose && exp.optimization_id && (
              <span>
                <Tag color="purple">{purpose.zh} {purpose.en}</Tag>
                <Link to={`/optimizations/${exp.optimization_id}`}><code>{exp.optimization_id}</code></Link>
              </span>
            )}
            <span>场景 Scenario：{exp.scenario.name_zh}</span>
            <span>后端 Backend：{exp.backend.id}{exp.backend.version ? ` ${exp.backend.version}` : ''}</span>
            <span>创建 Created：{formatDateTime(exp.created_at)}</span>
            {exp.finished_at && <span>完成 Finished：{formatDateTime(exp.finished_at)}</span>}
          </Space>
        }
      />

      {failed && (
        <Alert
          type="error"
          showIcon
          className="section-bottom"
          title="实验执行失败 Experiment Failed"
          description={
            exp.error ? (
              <span>
                <code>{exp.error.code}</code> · {exp.error.message}
              </span>
            ) : (
              '后端未返回错误详情 / No error detail'
            )
          }
        />
      )}
      {isActiveStatus(exp.status) && (
        <Alert type="info" showIcon className="section-bottom" title="实验正在执行，页面将自动刷新。Experiment in progress." />
      )}
      {(exp.warnings ?? []).map((w) => (
        <Alert key={w} type="warning" showIcon className="section-bottom" title={w} />
      ))}

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Card title={sectionTitle('无线电地图', 'Radio Map')} className="radio-map-card">
            <RadioMap experiment={exp} maxHeight="62vh" />
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card title={sectionTitle('仿真指标', 'Simulation Metrics')} size="small">
            <MetricsSection experiment={exp} />
          </Card>
          <Card title={sectionTitle('运行耗时', 'Runtime')} size="small" className="section">
            <RuntimePanel runtime={exp.runtime} />
          </Card>
        </Col>
      </Row>

      <SystemKpiSection />

      <Row gutter={[16, 16]} className="section">
        <Col xs={24} lg={8}>
          <Card title={sectionTitle('数据来源', 'Provenance')} size="small" className="fill-height">
            <ProvenancePanel experiment={exp} />
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card title={sectionTitle('时间线', 'Timeline')} size="small" className="fill-height">
            <StatusTimeline history={exp.status_history ?? []} />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={sectionTitle('实验产物', 'Artifacts')} size="small" className="fill-height">
            <ArtifactsPanel artifacts={exp.artifacts ?? []} />
          </Card>
        </Col>
      </Row>
    </>
  );
}
