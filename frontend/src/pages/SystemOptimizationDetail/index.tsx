import { ArrowLeftOutlined, LoadingOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Row, Skeleton, Space, Steps, Tag } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';

import { useSystemOptimization } from '../../api/systemOptimizations';
import { ArtifactsPanel } from '../../components/ArtifactsPanel';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import { StatusTag } from '../../components/StatusTag';
import type { SystemOptimizationResponse } from '../../types/systemOptimization';
import { formatDateTime, formatSeconds } from '../../utils/format';
import {
  findCandidate,
  isIterativeRun,
  parameterSpaceText,
  progressText,
  RUNNING_STAGES,
  stageLabel,
} from '../../utils/systemOptimization';
import { AlgorithmRunPanel } from './AlgorithmRunPanel';
import { AlgorithmTraceChart } from './AlgorithmTraceChart';
import { AlgorithmTraceTable } from './AlgorithmTraceTable';
import { CandidateHistoryChart } from './CandidateHistoryChart';
import { EvidencePanel } from './EvidencePanel';
import { EvaluationProtocolPanel } from './EvaluationProtocolPanel';
import { HeroComparison } from './HeroComparison';
import { PerUeComparison } from './PerUeComparison';
import { SystemCandidateTable } from './SystemCandidateTable';
import { SystemOptimizationProvenance } from './SystemOptimizationProvenance';

const LIST_PATH = '/optimizations?type=system';

function sectionTitle(zh: string, en: string) {
  return (
    <span>
      {zh} <span className="card-title-en">{en}</span>
    </span>
  );
}

function RunningStages({ o }: { o: SystemOptimizationResponse }) {
  const current = RUNNING_STAGES.indexOf(o.progress.stage);
  return (
    <Card className="section-bottom" data-testid="running-stages">
      <Steps
        size="small"
        current={Math.max(current, 0)}
        items={RUNNING_STAGES.map((stage, i) => ({
          title: stageLabel(stage).en,
          content: stageLabel(stage).zh,
          icon: i === current ? <LoadingOutlined /> : undefined,
        }))}
      />
      <div className="section" data-testid="progress-text">
        <Tag color="processing">{progressText(o.progress)}</Tag>
        <span className="muted">
          页面每 2 秒刷新真实阶段（不做百分比估计）。Real stages, refreshed every 2 s.
        </span>
      </div>
    </Card>
  );
}

export function SystemOptimizationDetailPage() {
  const { optimizationId = '' } = useParams();
  const navigate = useNavigate();
  const query = useSystemOptimization(optimizationId);
  const o = query.data;

  const back = (
    <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(LIST_PATH)}>
      返回优化中心
    </Button>
  );

  if (query.isLoading) {
    return (
      <>
        <PageHeader titleZh="系统级优化详情" titleEn="System Optimization Detail" extra={back} />
        <Skeleton active paragraph={{ rows: 12 }} />
      </>
    );
  }
  if (query.isError || !o) {
    return (
      <>
        <PageHeader titleZh="系统级优化详情" titleEn="System Optimization Detail" extra={back} />
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      </>
    );
  }

  const active = o.status === 'created' || o.status === 'running';
  const best = findCandidate(o, o.best_candidate_id);
  const ctx = o.evaluation_context;
  const trace = o.algorithm_trace;
  const iterative = isIterativeRun(o);
  const algorithmLabel = o.algorithm ? `${o.algorithm.algorithm_name_en} v${o.algorithm.algorithm_version}`
    : `${o.optimizer_id} v${o.optimizer_version}`;

  return (
    <>
      <PageHeader
        titleZh="系统级优化详情"
        titleEn="System Optimization Detail"
        extra={back}
        subtitle={
          <Space wrap size={[16, 4]} className="experiment-meta">
            <code className="experiment-meta__id">{o.optimization_id}</code>
            <StatusTag status={o.status} showEn />
            <span>场景 Scenario：{o.scenario_name_zh} <span className="muted">{o.scenario_id}</span></span>
            <span>算法 Algorithm：{algorithmLabel}</span>
            <span>目标 Objective：{o.objective.id} <Tag color="blue">v{o.objective.version}</Tag></span>
            <span>变量 Variable：<code>{o.parameter.id}</code></span>
            <span>协议 Protocol：{o.benchmark_protocol.protocol_id} v{o.benchmark_protocol.version}</span>
            <span>后端 Backend：{o.backend_id}</span>
            <span>总耗时 Runtime：{formatSeconds(o.runtime.total_seconds, 1)}</span>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        className="section-bottom"
        data-testid="scientific-boundary"
        title={o.scientific_boundary_zh}
        description={
          <>
            <div>{o.optimizer_notice_zh}</div>
            <div className="muted">{o.scientific_boundary_en} {o.optimizer_notice_en}</div>
          </>
        }
      />

      {active && <RunningStages o={o} />}

      {o.status === 'failed' && (
        <Alert
          type="error"
          showIcon
          className="section-bottom"
          title="系统级优化失败 System Optimization Failed"
          description={
            o.error ? (
              <span>
                <code>{o.error.code}</code> · {o.error.message}
                {o.error.failed_candidate_id && <> · 失败候选 <code>{o.error.failed_candidate_id}</code></>}
              </span>
            ) : (
              '后端未返回错误详情 / No error detail'
            )
          }
        />
      )}

      {o.warnings.map((w) => (
        <Alert key={w} type="warning" showIcon className="section-bottom" title={w} data-testid="optimization-warning" />
      ))}

      <HeroComparison optimization={o} />

      <Card size="small" title={sectionTitle('算法', 'Algorithm')} className="section-bottom">
        <AlgorithmRunPanel optimization={o} />
      </Card>

      {iterative && trace && trace.evaluations.length > 0 && (
        <Row gutter={[16, 16]} className="section-bottom">
          <Col xs={24} xl={12}>
            <Card size="small" title={sectionTitle('算法轨迹', 'Algorithm Trace')} className="fill-height"
              data-testid="algorithm-trace">
              <AlgorithmTraceChart trace={trace} parameterId={o.parameter.id} />
              <div className="muted">
                每个点是一次真实评价；阶梯线为平台规则下的当前最优（记录值，非拟合曲线）。Each point is a real evaluation.
              </div>
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card size="small" title={sectionTitle('参数—目标', 'Parameter vs Objective')} className="fill-height">
              <CandidateHistoryChart
                candidates={o.baseline ? [o.baseline, ...o.candidates] : o.candidates}
                baseline={o.baseline}
                bestCandidateId={o.best_candidate_id}
                parameterId={o.parameter.id}
              />
            </Card>
          </Col>
        </Row>
      )}

      {iterative && trace && trace.rounds.length > 0 && (
        <Card size="small" title={sectionTitle('算法轮次', 'Algorithm Rounds')} className="section-bottom">
          <AlgorithmTraceTable trace={trace} parameterId={o.parameter.id} />
        </Card>
      )}

      {(o.baseline || o.candidates.length > 0) && (
        <Row gutter={[16, 16]} className="section-bottom">
          {!iterative && (
            <Col xs={24} xl={best && o.baseline ? 12 : 24}>
              <Card size="small" title={sectionTitle('候选评价历史', 'Candidate History')} className="fill-height">
                <CandidateHistoryChart
                  candidates={o.baseline ? [o.baseline, ...o.candidates] : o.candidates}
                  baseline={o.baseline}
                  bestCandidateId={o.best_candidate_id}
                  parameterId={o.parameter.id}
                />
                <div className="muted">Grid Search 逐点评估，点之间不代表连续优化过程。Discrete evaluations only.</div>
              </Card>
            </Col>
          )}
          {best && o.baseline && o.status === 'succeeded' && (
            <Col xs={24} xl={iterative ? 24 : 12}>
              <Card size="small" title={sectionTitle('逐 UE 对比', 'Per-UE Before / After')} className="fill-height">
                <PerUeComparison baseline={o.baseline} best={best} />
              </Card>
            </Col>
          )}
        </Row>
      )}

      <Card size="small" title={sectionTitle('候选列表', 'Candidates')} className="section-bottom">
        <SystemCandidateTable
          optimizationId={o.optimization_id}
          parameterId={o.parameter.id}
          baseline={o.baseline}
          candidates={o.candidates}
          bestCandidateId={o.best_candidate_id}
        />
        {o.comparison && <div className="muted section">平局规则 Tie-break：{o.comparison.tie_break_rule}</div>}
      </Card>

      <Card size="small" title={sectionTitle('评估协议', 'Evaluation Protocol')} className="section-bottom">
        <EvaluationProtocolPanel optimization={o} />
      </Card>

      <Row gutter={[16, 16]} className="section-bottom">
        <Col xs={24} lg={12}>
          <Card size="small" title={sectionTitle('优化目标', 'Objective')} className="fill-height" data-testid="objective-detail">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="目标 Objective">{o.objective.id} v{o.objective.version}</Descriptions.Item>
              <Descriptions.Item label="方向 Direction">{o.objective.direction}</Descriptions.Item>
              <Descriptions.Item label="定义 Definition"><code>J = NETWORK_THROUGHPUT_V0_1 (Mbps)</code></Descriptions.Item>
              <Descriptions.Item label="变量 Variable">
                {o.parameter.name_zh} {o.parameter.name_en} <span className="muted">({o.parameter.source})</span>
              </Descriptions.Item>
              <Descriptions.Item label="参数空间 Parameter Space">{parameterSpaceText(o)}</Descriptions.Item>
              <Descriptions.Item label="验收 KPI Acceptance KPI"><Tag>No</Tag></Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={sectionTitle('数据来源', 'Provenance')} className="fill-height">
            <SystemOptimizationProvenance optimization={o} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card size="small" title={sectionTitle('运行耗时', 'Runtime')} className="fill-height">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="上下文 Context (RT)">{formatSeconds(o.runtime.context_seconds, 2)}</Descriptions.Item>
              <Descriptions.Item label="基线 Baseline">{formatSeconds(o.runtime.baseline_seconds, 2)}</Descriptions.Item>
              <Descriptions.Item label="候选 Candidates">{formatSeconds(o.runtime.candidate_evaluation_seconds, 2)}</Descriptions.Item>
              <Descriptions.Item label="总计 Total">{formatSeconds(o.runtime.total_seconds, 2)}</Descriptions.Item>
              <Descriptions.Item label="创建 Created">{formatDateTime(o.created_at)}</Descriptions.Item>
              {ctx && <Descriptions.Item label="Context">{ctx.context_id}</Descriptions.Item>}
            </Descriptions>
            <div className="muted">平台运行耗时，不是优化速度验收指标。Platform runtime, not an acceptance KPI.</div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={sectionTitle('证据状态', 'Evidence')} className="section-bottom">
            <EvidencePanel descriptor={o.evidence_descriptor} />
          </Card>
          <Card size="small" title={sectionTitle('证据文件', 'Artifacts')}>
            <ArtifactsPanel
              artifacts={o.artifact_links.map((a) => ({ ...a, type: a.media_type.split('/').pop() ?? 'binary' }))}
            />
          </Card>
        </Col>
      </Row>
    </>
  );
}
