import { ArrowLeftOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Row, Steps, Table, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';

import { useAlgorithms } from '../../api/algorithms';
import { PageHeader } from '../../components/PageHeader';
import { ALGORITHMS_PATH } from '../../utils/algorithm';

const LIFECYCLE = [
  { title: 'metadata()', content: '身份 / 能力 / 超参数 schema' },
  { title: 'initialize()', content: '参数空间、超参数、基线' },
  { title: 'suggest()', content: '下一批候选（≤ 剩余预算）' },
  { title: 'platform evaluate', content: '平台在冻结上下文中仿真' },
  { title: 'observe()', content: '收到目标值反馈' },
  { title: 'should_stop()', content: 'stop reason' },
  { title: 'finalize()', content: '推荐参数' },
];

const RESPONSIBILITY = [
  { key: 'a', algorithm: '决定下一批参数值', platform: '场景、冻结信道 / UE / 业务、Sionna 仿真' },
  { key: 'b', algorithm: '根据目标值反馈更新状态', platform: 'KPI、目标函数、最优选择、公平性检查' },
  { key: 'c', algorithm: '决定何时停止', platform: '评价预算（强制）、缓存、trace、证据导出' },
];

const STEPS = [
  ['1. 实现接口', '继承 algorithms.Algorithm，实现 metadata / initialize / suggest / observe / should_stop / finalize。'],
  ['2. 声明能力', 'AlgorithmCapabilities 只把真实支持的参数类型置为 true；不支持的类型在运行前返回 422。'],
  ['3. 声明超参数', 'HyperparameterDefinition（float / integer / boolean / categorical），每个都要有推荐默认值。'],
  ['4. 本地测试', '用 FakeSystemBackend（tests/system_helpers.py）数秒跑完整链路，不需要 Sionna。'],
  ['5. 注册', '在 src/algorithms/registry.py 的 default_algorithm_registry() 中 registry.register(MyOptimizer)。'],
  ['6. 运行', '优化中心 → 新建系统级优化 → 选择算法；或 POST /api/v1/system-optimizations。'],
  ['7. 证据', '平台自动导出 trace / 配置 / 哈希；scripts/verify_algorithm_run.py 独立复核。复核 ≠ 验收。'],
];

export function IntegrationGuidePage() {
  const navigate = useNavigate();
  const list = useAlgorithms();
  return (
    <>
      <PageHeader
        titleZh="算法接入说明"
        titleEn="How to Integrate an Algorithm"
        extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ALGORITHMS_PATH)}>返回算法中心</Button>}
        subtitle={<span>Algorithm SDK v{list.data?.sdk_version ?? '—'} · 目标读者：项目科研团队</span>}
      />
      <Alert
        type="info"
        showIcon
        className="section-bottom"
        title="平台拥有仿真、KPI、目标函数、预算与证据；算法只负责生成候选。算法不能访问 Sionna、KPI 实现或实验仓库。"
        description="The platform owns simulation, KPIs, objective, budget and evidence; an algorithm only proposes candidates."
      />
      <Card size="small" className="section-bottom" title={<span>生命周期 <span className="card-title-en">Lifecycle</span></span>}>
        <Steps size="small" current={-1} items={LIFECYCLE} data-testid="integration-lifecycle" />
      </Card>
      <Row gutter={[16, 16]} className="section-bottom">
        <Col xs={24} lg={12}>
          <Card size="small" className="fill-height" title={<span>职责划分 <span className="card-title-en">Responsibilities</span></span>}>
            <Table
              size="small"
              pagination={false}
              dataSource={RESPONSIBILITY}
              columns={[
                { title: '算法 Algorithm', dataIndex: 'algorithm' },
                { title: '平台 Platform', dataIndex: 'platform' },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" className="fill-height" title={<span>文档 <span className="card-title-en">Documents</span></span>}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="接入契约 Contract"><code>{list.data?.integration_contract ?? '—'}</code></Descriptions.Item>
              <Descriptions.Item label="接入指南 Guide"><code>{list.data?.integration_guide ?? '—'}</code></Descriptions.Item>
              <Descriptions.Item label="示例模板 Template">
                <code>src/algorithms/examples/research_demo_optimizer/</code>
              </Descriptions.Item>
              <Descriptions.Item label="独立复核 Verifier"><code>scripts/verify_algorithm_run.py</code></Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
      <Card size="small" className="section-bottom" title={<span>接入步骤 <span className="card-title-en">Steps</span></span>}
        data-testid="integration-steps">
        <Descriptions column={1} size="small" bordered>
          {STEPS.map(([title, text]) => (
            <Descriptions.Item key={title} label={title}>{text}</Descriptions.Item>
          ))}
        </Descriptions>
      </Card>
      <Card size="small" title={<span>兼容性错误代码 <span className="card-title-en">Compatibility Codes (HTTP 422)</span></span>}>
        {[
          'ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED',
          'ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED',
          'ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED',
          'ALGORITHM_CONSTRAINTS_NOT_SUPPORTED',
          'ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED',
          'INVALID_HYPERPARAMETER',
          'INVALID_EVALUATION_BUDGET',
        ].map((c) => <Tag key={c}>{c}</Tag>)}
      </Card>
    </>
  );
}
