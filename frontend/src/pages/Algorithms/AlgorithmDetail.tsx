import { ArrowLeftOutlined, BookOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Row, Skeleton, Space, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useAlgorithm } from '../../api/algorithms';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import type { AlgorithmCapabilities, HyperparameterDefinition } from '../../types/algorithm';
import { ALGORITHMS_PATH, formatHyperparameter, INTEGRATION_GUIDE_PATH, parameterTypeLabel } from '../../utils/algorithm';
import { systemOptimizationPath } from '../../utils/systemOptimization';
import { AlgorithmTags } from './AlgorithmTags';

const CAPABILITY_LABELS: [keyof Omit<AlgorithmCapabilities, 'max_parameters'>, string][] = [
  ['supports_continuous', '连续参数 Continuous'],
  ['supports_discrete', '离散参数 Discrete'],
  ['supports_integer', '整数参数 Integer'],
  ['supports_categorical', '类别参数 Categorical'],
  ['supports_vector', '向量参数 Vector'],
  ['supports_constraints', '约束 Constraints'],
  ['supports_multi_objective', '多目标 Multi-objective'],
  ['supports_batch_suggestions', '批量建议 Batch Suggestions'],
  ['supports_iterative_feedback', '迭代反馈 Iterative Feedback'],
  ['supports_auto_configuration', '自动配置 Auto Configuration'],
];

const hpColumns: ColumnsType<HyperparameterDefinition> = [
  { title: 'ID', dataIndex: 'id', render: (v: string) => <code>{v}</code> },
  { title: '名称 Name', key: 'name', render: (_, h) => <>{h.name_zh} <span className="muted">{h.name_en}</span></> },
  { title: '类型 Type', dataIndex: 'type' },
  { title: '推荐默认 Default', key: 'default', render: (_, h) => formatHyperparameter(h.default) },
  {
    title: '范围 Range',
    key: 'range',
    render: (_, h) =>
      h.bounds
        ? `${h.bounds.lower_inclusive ? '[' : '('}${h.bounds.lower}, ${h.bounds.upper}${h.bounds.upper_inclusive ? ']' : ')'}`
        : h.choices
          ? h.choices.map(String).join(' / ')
          : '—',
  },
  { title: '说明 Description', key: 'desc', render: (_, h) => h.description_zh || h.description_en || '—' },
];

export function AlgorithmDetailPage() {
  const { algorithmId = '' } = useParams();
  const navigate = useNavigate();
  const query = useAlgorithm(algorithmId);
  const back = (
    <Space>
      <Button icon={<BookOutlined />} onClick={() => navigate(INTEGRATION_GUIDE_PATH)}>接入说明 Guide</Button>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ALGORITHMS_PATH)}>返回算法中心</Button>
    </Space>
  );
  if (query.isLoading) {
    return (
      <>
        <PageHeader titleZh="算法详情" titleEn="Algorithm Detail" extra={back} />
        <Skeleton active paragraph={{ rows: 10 }} />
      </>
    );
  }
  if (query.isError || !query.data) {
    return (
      <>
        <PageHeader titleZh="算法详情" titleEn="Algorithm Detail" extra={back} />
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      </>
    );
  }
  const { metadata: m, evidence: e } = query.data;
  const caps = m.capabilities;
  return (
    <>
      <PageHeader
        titleZh={m.name_zh}
        titleEn={m.name_en}
        extra={back}
        subtitle={
          <Space wrap size={[16, 4]}>
            <code>{m.algorithm_id}</code>
            <span>v{m.version}</span>
            <span>SDK {m.sdk_version}</span>
            <AlgorithmTags category={m.category} status={m.status} learning={m.learning_algorithm}
              deliverable={m.project_research_deliverable} />
          </Space>
        }
      />
      <Alert type="info" showIcon className="section-bottom" data-testid="algorithm-notice" title={query.data.notice_zh}
        description={query.data.notice_en} />
      <Row gutter={[16, 16]} className="section-bottom">
        <Col xs={24} lg={14}>
          <Card size="small" title={<span>算法说明 <span className="card-title-en">Metadata</span></span>} className="fill-height">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="描述 Description">
                {m.description_zh}
                <div className="muted">{m.description_en}</div>
              </Descriptions.Item>
              <Descriptions.Item label="用途 Purpose">{m.purpose_zh} <span className="muted">{m.purpose_en}</span></Descriptions.Item>
              <Descriptions.Item label="提供方 Provider">{m.provider}</Descriptions.Item>
              <Descriptions.Item label="学习算法 Learning">{m.learning_algorithm ? 'Yes' : 'No'}</Descriptions.Item>
              <Descriptions.Item label="科研成果 Research Deliverable">{m.project_research_deliverable ? 'Yes' : 'No'}</Descriptions.Item>
              <Descriptions.Item label="验收算法 Acceptance Algorithm">{m.acceptance_algorithm ? 'Yes' : 'No'}</Descriptions.Item>
              <Descriptions.Item label="问题类型 Problem Types">{m.supported_problem_types.join(', ')}</Descriptions.Item>
              <Descriptions.Item label="源码 Source"><code>{m.source}</code></Descriptions.Item>
              <Descriptions.Item label="标签 Labels">{m.labels.map((l) => <Tag key={l}>{l}</Tag>)}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card size="small" title={<span>证据状态 <span className="card-title-en">Evidence Status</span></span>}
            className="fill-height" data-testid="algorithm-evidence">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="优化运行 Runs">{e.optimization_runs}</Descriptions.Item>
              <Descriptions.Item label="成功 Succeeded">{e.succeeded_runs}</Descriptions.Item>
              <Descriptions.Item label="最近成功 Latest">
                {e.latest_succeeded_optimization_id ? (
                  <Link to={systemOptimizationPath(e.latest_succeeded_optimization_id)}>
                    <code>{e.latest_succeeded_optimization_id}</code>
                  </Link>
                ) : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="可作验收证据 Acceptance-eligible">
                <Tag>{e.acceptance_eligible_runs}</Tag>
              </Descriptions.Item>
            </Descriptions>
            <div className="muted">
              所有运行均为仿真证据；复核通过 ≠ 验收通过。All runs are simulation evidence; verification ≠ acceptance.
            </div>
          </Card>
        </Col>
      </Row>
      <Card size="small" className="section-bottom" title={<span>能力声明 <span className="card-title-en">Capabilities</span></span>}
        data-testid="algorithm-capabilities">
        <Space wrap>
          {CAPABILITY_LABELS.map(([key, label]) => (
            <Tag key={key} color={caps[key] ? 'green' : 'default'}>{caps[key] ? '✓' : '✗'} {label}</Tag>
          ))}
          <Tag>最大参数数 Max Parameters: {caps.max_parameters ?? '∞'}</Tag>
        </Space>
        <div className="muted section">
          支持的参数类型 Supported: {m.supported_parameter_types.map(parameterTypeLabel).join(', ')}
        </div>
      </Card>
      <Card size="small" title={<span>超参数 <span className="card-title-en">Hyperparameter Schema</span></span>}>
        {m.hyperparameter_schema.length > 0 ? (
          <Table rowKey="id" size="small" pagination={false} columns={hpColumns} dataSource={m.hyperparameter_schema} />
        ) : (
          <div className="muted">无算法超参数。No hyperparameters.</div>
        )}
        <div className="muted section">超参数与网络优化变量分离。Hyperparameters are separate from network variables.</div>
      </Card>
    </>
  );
}
