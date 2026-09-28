import { Alert, Button, Card, Col, Collapse, Descriptions, Empty, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { Link } from 'react-router-dom';

import { useBenchmarkAlgorithms, useBenchmarkProtocols, useBenchmarks, useCreateBenchmark } from '../../api/benchmarks';

const { Title, Text } = Typography;

export function BenchmarkCenterPage() {
  const algorithms = useBenchmarkAlgorithms();
  const protocols = useBenchmarkProtocols();
  const benchmarks = useBenchmarks();
  const create = useCreateBenchmark();
  const latest = benchmarks.data?.[0];
  const protocol = protocols.data?.[0] as Record<string, any> | undefined;

  if (algorithms.isError || protocols.isError) return <Empty description="Benchmark catalog unavailable" />;
  return (
    <Space orientation="vertical" size="large" style={{ width: '100%' }}>
      <div><Title level={2} style={{ marginBottom: 4 }}>算法基准与对比</Title><Text type="secondary">Benchmark Center · Same protocol, fair comparison</Text></div>
      <Alert type="info" showIcon title="比较展示证据，不自动宣布冠军" description="所有算法共享 MULTICELL-DEMO-001、Day 8 冻结信道、目标函数、P5 约束和 evaluation budget。单次 repeat 不展示统计显著性。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}><Card title="Runnable Algorithms" extra={<Space><Tag color="blue">仿真</Tag><Tag color="green">✓ 已验证</Tag></Space>}>
          <Table rowKey="algorithm_id" pagination={false} dataSource={algorithms.data?.runnable ?? []} columns={[
            { title: 'Algorithm', dataIndex: 'name' }, { title: 'Category', dataIndex: 'category' },
            { title: 'Learning?', render: (_: unknown, row: any) => String(row.learning_algorithm) },
            { title: 'Compatibility', render: (_: unknown, row: any) => <Tag color={row.compatibility.status === 'compatible' ? 'green' : 'orange'}>{row.compatibility.status}</Tag> },
          ]} />
        </Card></Col>
        <Col xs={24} lg={10}><Card title="Protocol / Evaluation Context">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Protocol">{protocol?.protocol_id} v{protocol?.version}</Descriptions.Item>
            <Descriptions.Item label="Problem">{protocol?.problem_type}</Descriptions.Item>
            <Descriptions.Item label="Scenario">MULTICELL-DEMO-001</Descriptions.Item>
            <Descriptions.Item label="Budget">{protocol?.evaluation_budget} evaluations</Descriptions.Item>
            <Descriptions.Item label="Objective">{protocol?.objective?.id}</Descriptions.Item>
            <Descriptions.Item label="Constraint">P5 ≥ baseline P5</Descriptions.Item>
          </Descriptions>
          <Button type="primary" loading={create.isPending} onClick={() => create.mutate({ scenario_id: 'MULTICELL-DEMO-001', evaluation_budget: protocol?.evaluation_budget ?? 8 })}>运行基准 / Run benchmark</Button>
        </Card></Col>
      </Row>
      <Card title="Research Catalog · Not Runnable">
        <Collapse items={(algorithms.data?.research ?? []).map((item) => ({ key: item.reference_id, label: `${item.reference_id} · ${item.implementation_status}`, children: <Text>{item.paper_title} — {item.notes}</Text> }))} />
      </Card>
      {create.data && <Card title={`Comparison · ${create.data.benchmark_id}`} extra={<Tag color="green">comparison_eligible: YES</Tag>}>
        <Row gutter={16} style={{ marginBottom: 16 }}><Col><Statistic title="Scenario" value="MULTICELL-DEMO-001" /></Col><Col><Statistic title="Repeats" value={1} /></Col><Col><Statistic title="Channel" value={create.data.provenance.channel_hash.slice(0, 12)} /></Col></Row>
        <Table rowKey="benchmark_run_id" pagination={false} dataSource={create.data.results as any[]} columns={[
          { title: 'Algorithm', dataIndex: 'algorithm_id' }, { title: 'Category', dataIndex: 'category' },
          { title: 'Network Mbps', dataIndex: 'network_throughput_mbps', render: (v: number) => v.toFixed(2) },
          { title: 'P5 Mbps', dataIndex: 'p5_ue_throughput_mbps', render: (v: number) => v.toFixed(2) },
          { title: 'Feasible', dataIndex: 'feasible', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{String(v)}</Tag> },
          { title: 'Evaluations', dataIndex: 'evaluations_used' }, { title: 'Stop reason', dataIndex: 'stop_reason' },
        ]} />
      </Card>}
      {!create.data && latest && <Card title={`Latest benchmark · ${latest.benchmark_id}`}><Space orientation="vertical"><Text>已保存 benchmark reference；可再次运行生成同协议的新 run。</Text><Link to={`/benchmarks/${latest.benchmark_id}`}>Open persisted benchmark detail</Link></Space></Card>}
      {create.data && <Link to={`/benchmarks/${create.data.benchmark_id}`}>Open persisted benchmark detail</Link>}
      {create.isError && <Alert type="error" message="Benchmark run failed" description={create.error instanceof Error ? create.error.message : 'Unknown error'} />}
    </Space>
  );
}
