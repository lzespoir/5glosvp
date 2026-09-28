import { BookOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Row, Skeleton, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';

import { useAlgorithms } from '../../api/algorithms';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import type { AlgorithmSummary } from '../../types/algorithm';
import { algorithmPath, INTEGRATION_GUIDE_PATH, parameterTypeLabel } from '../../utils/algorithm';
import { AlgorithmTags } from './AlgorithmTags';

function AlgorithmCard({ a }: { a: AlgorithmSummary }) {
  const navigate = useNavigate();
  return (
    <Card
      hoverable
      className="fill-height clickable-card"
      data-testid={`algorithm-card-${a.id}`}
      onClick={() => navigate(algorithmPath(a.id))}
      title={
        <span>
          {a.name_zh} <span className="card-title-en">{a.name_en}</span>
        </span>
      }
      extra={<code>v{a.version}</code>}
    >
      <div className="section-bottom">
        <AlgorithmTags category={a.category} status={a.status} learning={a.learning_algorithm}
          deliverable={a.project_research_deliverable} />
      </div>
      <Descriptions column={1} size="small">
        <Descriptions.Item label="算法 ID">
          <code>{a.id}</code>
        </Descriptions.Item>
        <Descriptions.Item label="用途 Purpose">
          {a.purpose_zh} <span className="muted">{a.purpose_en}</span>
        </Descriptions.Item>
        <Descriptions.Item label="参数类型 Parameter Types">
          {a.supported_parameter_types.map((t) => <Tag key={t}>{parameterTypeLabel(t)}</Tag>)}
        </Descriptions.Item>
        <Descriptions.Item label="问题类型 Problem Types">{a.supported_problem_types.join(', ')}</Descriptions.Item>
        <Descriptions.Item label="迭代反馈 Iterative Feedback">
          {a.capabilities.supports_iterative_feedback ? 'Yes' : 'No'}
        </Descriptions.Item>
        <Descriptions.Item label="SDK">{a.sdk_version}</Descriptions.Item>
      </Descriptions>
      <div className="muted section">{a.notice_zh}</div>
    </Card>
  );
}

export function AlgorithmsPage() {
  const navigate = useNavigate();
  const query = useAlgorithms();
  const guide = (
    <Button icon={<BookOutlined />} onClick={() => navigate(INTEGRATION_GUIDE_PATH)}>
      算法接入说明 Integration Guide
    </Button>
  );
  return (
    <>
      <PageHeader
        titleZh="算法中心"
        titleEn="Algorithm Center"
        extra={guide}
        subtitle={query.data ? <span>Algorithm SDK v{query.data.sdk_version} · 静态注册 Static Registry</span> : null}
      />
      <Alert
        type="info"
        showIcon
        className="section-bottom"
        title="平台当前没有项目科研算法或学习优化算法；目录中的算法均为工程基线或接入验证算法。"
        description="No project research algorithm or learning optimizer is registered yet. Listed algorithms are an engineering baseline and an integration demo."
      />
      {query.isError ? (
        <Card><ErrorState error={query.error} onRetry={() => query.refetch()} /></Card>
      ) : !query.data ? (
        <Card><Skeleton active /></Card>
      ) : (
        <Row gutter={[16, 16]}>
          {query.data.items.map((a) => (
            <Col key={a.id} xs={24} lg={12}>
              <AlgorithmCard a={a} />
            </Col>
          ))}
        </Row>
      )}
    </>
  );
}
