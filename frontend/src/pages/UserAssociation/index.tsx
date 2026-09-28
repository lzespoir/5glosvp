import { Alert, Button, Card, Col, Descriptions, Empty, List, Row, Space, Statistic, Tag, Typography } from 'antd';
import { useState } from 'react';

import { useCreateUserAssociationOptimization, useMultiCellScenario, useMultiCellScenarios } from '../../api/userAssociation';

const { Title, Text } = Typography;

export function UserAssociationPage() {
  const { data: scenarios, isLoading, isError } = useMultiCellScenarios();
  const [selectedId, setSelectedId] = useState('MULTICELL-DEMO-001');
  const selected = scenarios?.find((item) => item.scenario_id === selectedId) ?? scenarios?.[0];
  const scenario = useMultiCellScenario(selected?.scenario_id ?? '');
  const create = useCreateUserAssociationOptimization();
  const detail = scenario.data ?? selected;

  if (isLoading) return <Card loading />;
  if (isError || !detail) return <Empty description="暂无多小区用户关联场景 / No multi-cell scenario" />;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ marginBottom: 4 }}>多小区用户关联优化</Title>
        <Text type="secondary">Multi-cell User Association · 冻结信道上的仿真优化验证</Text>
      </div>
      <Alert type="info" showIcon message="仿真边界 / Simulation boundary" description="本页面仅展示 Sionna RT 生成的冻结多小区信道；结果不代表实测、现网或华为验收数据。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title="场景 / Scenario">
            <List
              dataSource={scenarios ?? []}
              renderItem={(item) => (
                <List.Item actions={[<Button type={item.scenario_id === detail.scenario_id ? 'primary' : 'default'} size="small" onClick={() => setSelectedId(item.scenario_id)}>选择</Button>]}>
                  <List.Item.Meta title={item.name_zh} description={`${item.scenario_id} · ${item.ue_count} UEs`} />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title={`${detail.name_zh} / ${detail.name_en}`} extra={<Tag color="blue">simulation-only</Tag>}>
            <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
              <Descriptions.Item label="Cells">{detail.cells.length}</Descriptions.Item>
              <Descriptions.Item label="UEs">{detail.ue_count}</Descriptions.Item>
              <Descriptions.Item label="Candidate K">{detail.candidate_k}</Descriptions.Item>
              <Descriptions.Item label="Channel">{detail.channel.model}</Descriptions.Item>
              <Descriptions.Item label="Frozen">{detail.channel.frozen ? 'Yes' : 'No'}</Descriptions.Item>
              <Descriptions.Item label="Acceptance">{detail.simulation_only ? 'Not eligible' : 'Eligible'}</Descriptions.Item>
            </Descriptions>
            <Space wrap style={{ marginTop: 16 }}>
              {detail.cells.map((cell) => <Tag key={cell.cell_id}>{cell.cell_id} · {cell.tx_power_dbm} dBm</Tag>)}
            </Space>
            <Button type="primary" loading={create.isPending} style={{ marginTop: 20 }} onClick={() => create.mutate({ scenario_id: detail.scenario_id, evaluation_budget: 8 })}>运行关联优化 / Run association optimization</Button>
          </Card>
        </Col>
      </Row>
      {create.data && (
        <Card title={`结果 / Result · ${create.data.optimization_id}`}>
          <Row gutter={16}>
            <Col xs={12} md={6}><Statistic title="Baseline throughput" value={create.data.baseline.network_throughput_mbps} precision={2} suffix="Mbps" /></Col>
            <Col xs={12} md={6}><Statistic title="Best throughput" value={create.data.best.network_throughput_mbps} precision={2} suffix="Mbps" /></Col>
            <Col xs={12} md={6}><Statistic title="P5 floor" value={create.data.best.p5_throughput_mbps} precision={2} suffix="Mbps" /></Col>
            <Col xs={12} md={6}><Statistic title="Evaluations" value={create.data.evaluation_budget.evaluations_used} suffix={` / ${create.data.evaluation_budget.max_evaluations}`} /></Col>
          </Row>
          <Space style={{ marginTop: 16 }}><Tag color={create.data.best.feasible ? 'green' : 'orange'}>{create.data.best.feasible ? 'P5 floor feasible' : 'P5 floor not feasible'}</Tag><Tag>acceptance_eligible: {String(create.data.evidence?.acceptance_eligible ?? false)}</Tag><Tag>measured: {String(create.data.evidence?.measured ?? false)}</Tag></Space>
        </Card>
      )}
      {create.isError && <Alert type="error" message="优化请求失败 / Optimization request failed" description={create.error instanceof Error ? create.error.message : 'Unknown error'} />}
    </Space>
  );
}
