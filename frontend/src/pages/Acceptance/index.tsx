import { Alert, Card, Col, Descriptions, Row, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Link } from 'react-router-dom';

import { useEvidence } from '../../api/algorithms';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import type { EvidenceDescriptor } from '../../types/algorithm';
import { acceptanceReasonLabel, verificationMeta } from '../../utils/algorithm';
import { systemOptimizationPath } from '../../utils/systemOptimization';

type ItemStatus = 'not_confirmed' | 'not_available' | 'not_integrated' | 'not_started' | 'available';

function statusTag(s: ItemStatus) {
  switch (s) {
    case 'not_confirmed':
      return <Tag color="orange">未确认 Not Confirmed</Tag>;
    case 'not_available':
      return <Tag>无 Not Available</Tag>;
    case 'not_integrated':
      return <Tag>未接入 Not Integrated</Tag>;
    case 'not_started':
      return <Tag>未开始 Not Started</Tag>;
    case 'available':
      return <Tag color="green">已具备 Available</Tag>;
    default: {
      const unreachable: never = s;
      throw new Error(`Unknown acceptance item status: ${String(unreachable)}`);
    }
  }
}

/** 离散状态（不做进度百分比）：只陈述当前事实。 */
const ITEMS: { key: string; zh: string; en: string; status: ItemStatus }[] = [
  { key: 'kpi', zh: '验收 KPI 定义', en: 'Acceptance KPI definition', status: 'not_confirmed' },
  { key: 'measured', zh: '实测数据', en: 'Measured data', status: 'not_available' },
  { key: 'huawei', zh: '华为数据', en: 'Huawei data', status: 'not_available' },
  { key: 'research', zh: '项目科研算法', en: 'Project research algorithm', status: 'not_integrated' },
  { key: 'framework', zh: '算法接入框架', en: 'Algorithm integration framework', status: 'available' },
  { key: 'judgement', zh: '验收判定', en: 'Acceptance judgement', status: 'not_started' },
];

const columns: ColumnsType<EvidenceDescriptor> = [
  {
    title: '证据 Evidence',
    key: 'id',
    render: (_, e) => (
      <Link to={systemOptimizationPath(e.source_entity_id)}><code>{e.evidence_id}</code></Link>
    ),
  },
  { title: '算法 Algorithm', key: 'alg', render: (_, e) => <code>{String(e.provenance.algorithm ?? '—')}</code> },
  {
    title: '复核 Verification',
    key: 'ver',
    render: (_, e) => {
      const m = verificationMeta(e.verification_status);
      return <Tag color={m.color}>{m.en}</Tag>;
    },
  },
  {
    title: '可作验收证据 Acceptance-eligible',
    key: 'eligible',
    render: (_, e) => <Tag>{e.acceptance_eligible ? 'Yes' : 'No'}</Tag>,
  },
  {
    title: '原因 Reasons',
    key: 'reasons',
    render: (_, e) => e.acceptance_reason.map((r) => <Tag key={r}>{acceptanceReasonLabel(r)}</Tag>),
  },
];

export function AcceptancePage() {
  const evidence = useEvidence();
  const items = evidence.data?.items ?? [];
  return (
    <>
      <PageHeader titleZh="验收中心" titleEn="Acceptance Center" />
      <Alert
        type="warning"
        showIcon
        className="section-bottom"
        data-testid="acceptance-boundary"
        title="验收尚未开始：验收 KPI 未确认，没有实测 / 华为数据，也没有项目科研算法。以下仅列出现有仿真证据，均不可作为验收证据。"
        description="Acceptance has not started. Verification (independent re-computation) is not acceptance."
      />
      <Row gutter={[16, 16]} className="section-bottom">
        <Col xs={24} lg={10}>
          <Card size="small" className="fill-height" title={<span>验收前提 <span className="card-title-en">Prerequisites</span></span>}>
            <Descriptions column={1} size="small" data-testid="acceptance-status">
              {ITEMS.map((i) => (
                <Descriptions.Item key={i.key} label={`${i.zh} ${i.en}`}>{statusTag(i.status)}</Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card size="small" className="fill-height" title={<span>证据概况 <span className="card-title-en">Evidence Summary</span></span>}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="仿真证据 Simulation evidence">{evidence.data?.total ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="可作验收证据 Acceptance-eligible">
                <Tag>{items.filter((e) => e.acceptance_eligible).length}</Tag>
              </Descriptions.Item>
            </Descriptions>
            <div className="muted">
              独立复核结果保存在 reference/ 目录的 verification.json；平台记录中的状态为平台自检结果。
            </div>
          </Card>
        </Col>
      </Row>
      <Card size="small" title={<span>证据描述符 <span className="card-title-en">Evidence Descriptors</span></span>}>
        {evidence.isError ? (
          <ErrorState error={evidence.error} onRetry={() => evidence.refetch()} />
        ) : (
          <Table rowKey="evidence_id" size="small" columns={columns} dataSource={items} loading={evidence.isLoading}
            pagination={{ pageSize: 10, showSizeChanger: false }} />
        )}
      </Card>
    </>
  );
}
