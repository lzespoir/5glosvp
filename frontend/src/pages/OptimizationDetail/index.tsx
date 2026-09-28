import { ArrowLeftOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Row, Skeleton, Space, Tag } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';

import { useOptimization } from '../../api/optimizations';
import { ErrorState } from '../../components/ErrorState';
import { ObjectiveHistoryChart } from '../../components/ObjectiveHistoryChart';
import { PageHeader } from '../../components/PageHeader';
import { StatusTag } from '../../components/StatusTag';
import { formatDateTime, formatSeconds } from '../../utils/format';
import { candidatePower } from '../../utils/optimization';
import { BeforeAfter } from './BeforeAfter';
import { CandidateTable } from './CandidateTable';
import { ObjectiveBreakdown } from './ObjectiveBreakdown';
import { ObjectiveComparison } from './ObjectiveComparison';
import { OptimizationProvenance } from './OptimizationProvenance';
import { OptimizationTimeline } from './OptimizationTimeline';

export const SCIENTIFIC_NOTE =
  '当前优化目标为传播层工程目标函数，用于验证参数优化闭环。该指标不是项目最终吞吐率、边缘用户速率或优化速度验收指标。';

function sectionTitle(zh: string, en: string) {
  return (
    <span>
      {zh} <span className="card-title-en">{en}</span>
    </span>
  );
}

export function OptimizationDetailPage() {
  const { optimizationId = '' } = useParams();
  const navigate = useNavigate();
  const query = useOptimization(optimizationId);
  const opt = query.data;

  const back = (
    <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/optimizations')}>
      返回优化中心
    </Button>
  );

  if (query.isLoading) {
    return (
      <>
        <PageHeader titleZh="优化实验详情" titleEn="Optimization Detail" extra={back} />
        <Skeleton active paragraph={{ rows: 12 }} />
      </>
    );
  }

  if (query.isError || !opt) {
    return (
      <>
        <PageHeader titleZh="优化实验详情" titleEn="Optimization Detail" extra={back} />
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      </>
    );
  }

  const comparison = opt.comparison;
  const best = opt.best_candidate;
  const bestId = best?.candidate_id ?? null;

  return (
    <>
      <PageHeader
        titleZh="优化实验详情"
        titleEn="Optimization Detail"
        extra={back}
        subtitle={
          <Space wrap size={[16, 4]} className="experiment-meta">
            <code className="experiment-meta__id">{opt.optimization_id}</code>
            <StatusTag status={opt.status} showEn />
            <span>场景 Scenario：{opt.scenario.name_zh}</span>
            <span>优化器 Optimizer：{opt.optimizer.name_en ?? opt.optimizer.id}</span>
            <span>
              目标 Objective：{opt.objective.id} <Tag color="blue">v{opt.objective.version}</Tag>
            </span>
            <span>后端 Backend：{opt.simulation_backend}</span>
            <span>创建 Created：{formatDateTime(opt.created_at)}</span>
          </Space>
        }
      />

      {opt.status === 'failed' && (
        <Alert
          type="error"
          showIcon
          className="section-bottom"
          title="优化实验失败 Optimization Failed"
          description={
            opt.error ? (
              <span>
                <code>{opt.error.code}</code> · {opt.error.message}
                {opt.error.failed_candidate_id && <> · 失败候选 <code>{opt.error.failed_candidate_id}</code></>}
              </span>
            ) : (
              '后端未返回错误详情 / No error detail'
            )
          }
        />
      )}
      {(opt.status === 'created' || opt.status === 'running') && (
        <Alert type="info" showIcon className="section-bottom" title="优化正在执行，页面将自动刷新。Optimization in progress." />
      )}
      <Alert
        type="info"
        showIcon
        className="section-bottom"
        title="科学说明 Scientific Note"
        description={SCIENTIFIC_NOTE}
        data-testid="scientific-note"
      />

      {comparison && opt.improvement_status && (
        <>
          <BeforeAfter
            baselineExperimentId={comparison.baseline_experiment_id}
            optimizedExperimentId={comparison.optimized_experiment_id}
            baselinePower={candidatePower(opt.baseline)}
            optimizedPower={candidatePower(best)}
            baselineObjective={opt.baseline?.objective?.value}
            optimizedObjective={best?.objective?.value}
            optimizedCandidateId={comparison.optimized_candidate_id}
          />
          <div className="muted before-after__note">
            两张无线电地图各自使用独立色标（RSS dBm），比较时请以色标数值为准。Each map has its own color scale.
          </div>
          <Row gutter={[16, 16]} className="section">
            <Col xs={24} xl={8}>
              <ObjectiveComparison comparison={comparison} status={opt.improvement_status} />
            </Col>
            <Col xs={24} xl={16}>
              <Card size="small" title={sectionTitle('候选评价历史', 'Objective History')} className="fill-height">
                <ObjectiveHistoryChart candidates={opt.candidates} baseline={opt.baseline} bestCandidateId={bestId} />
              </Card>
            </Col>
          </Row>
          <div className="section">
            <ObjectiveBreakdown baseline={opt.baseline} best={best} formula={opt.objective.formula} />
          </div>
        </>
      )}

      <div className="section">
        <CandidateTable baseline={opt.baseline} candidates={opt.candidates} bestCandidateId={bestId} />
      </div>

      <Row gutter={[16, 16]} className="section">
        <Col xs={24} lg={9}>
          <Card size="small" title={sectionTitle('数据来源', 'Provenance')} className="fill-height">
            <OptimizationProvenance optimization={opt} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" title={sectionTitle('时间线', 'Timeline')} className="fill-height">
            <OptimizationTimeline events={opt.events} />
          </Card>
        </Col>
        <Col xs={24} lg={7}>
          <Card size="small" title={sectionTitle('运行耗时', 'Runtime')} className="fill-height">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="基线 Baseline">{formatSeconds(opt.runtime.baseline_seconds, 2)}</Descriptions.Item>
              <Descriptions.Item label="候选评价 Candidates">
                {formatSeconds(opt.runtime.candidate_evaluation_seconds, 2)}
              </Descriptions.Item>
              <Descriptions.Item label="总计 Total">{formatSeconds(opt.runtime.total_seconds, 2)}</Descriptions.Item>
            </Descriptions>
            <div className="muted">平台运行耗时，不是优化速度验收指标。Platform runtime, not an acceptance KPI.</div>
          </Card>
        </Col>
      </Row>
    </>
  );
}
