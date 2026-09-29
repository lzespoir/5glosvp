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

  if (algorithms.isError || protocols.isError) return <Empty description="基准目录暂不可用" />;
  return (
    <Space orientation="vertical" size="large" style={{ width: '100%' }}>
      <div><Title level={2} style={{ marginBottom: 4 }}>算法基准</Title><Text type="secondary">固定协议下的可复现实验参考；用户发起的对比请进入“对比分析”。</Text></div>
      <Alert type="info" showIcon title="基准与对比是两类对象" description="基准用于协议化运行；对比分析必须由用户选择运行记录、声明意图并确认创建，不自动宣布冠军。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}><Card title="可运行算法" extra={<Space><Tag color="blue">仿真</Tag><Tag color="green">平台检查通过</Tag></Space>}>
          <Table rowKey="algorithm_id" pagination={false} dataSource={algorithms.data?.runnable ?? []} columns={[
            { title: '算法', dataIndex: 'name' }, { title: '类别', dataIndex: 'category' },
            { title: '是否学习算法', render: (_: unknown, row: any) => row.learning_algorithm ? '是' : '否' },
            { title: '兼容性', render: (_: unknown, row: any) => <Tag color={row.compatibility.status === 'compatible' ? 'green' : 'orange'}>{row.compatibility.status === 'compatible' ? '兼容' : '需检查'}</Tag> },
          ]} />
        </Card></Col>
        <Col xs={24} lg={10}><Card title="协议与评价上下文">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Protocol">{protocol?.protocol_id} v{protocol?.version}</Descriptions.Item>
            <Descriptions.Item label="Problem">{protocol?.problem_type}</Descriptions.Item>
            <Descriptions.Item label="Scenario">MULTICELL-DEMO-001</Descriptions.Item>
            <Descriptions.Item label="评价预算">{protocol?.evaluation_budget} 次</Descriptions.Item>
            <Descriptions.Item label="目标">{protocol?.objective?.id}</Descriptions.Item>
            <Descriptions.Item label="约束">P5 ≥ 基线 P5</Descriptions.Item>
          </Descriptions>
          <Button type="primary" loading={create.isPending} onClick={() => create.mutate({ scenario_id: 'MULTICELL-DEMO-001', evaluation_budget: protocol?.evaluation_budget ?? 8 })}>运行协议基准</Button>{' '}<Link to="/comparisons">发起对比分析</Link>
        </Card></Col>
      </Row>
      <Card title="研究目录 · 当前不可运行">
        <Collapse items={(algorithms.data?.research ?? []).map((item) => ({ key: item.reference_id, label: `${item.reference_id} · ${item.implementation_status}`, children: <Text>{item.paper_title} — {item.notes}</Text> }))} />
      </Card>
      {create.data && <Card title={`基准结果 · ${create.data.benchmark_id}`} extra={<Tag color="green">可进入对比预览</Tag>}>
        <Row gutter={16} style={{ marginBottom: 16 }}><Col><Statistic title="Scenario" value="MULTICELL-DEMO-001" /></Col><Col><Statistic title="Repeats" value={1} /></Col><Col><Statistic title="Channel" value={create.data.provenance.channel_hash.slice(0, 12)} /></Col></Row>
        <Table rowKey="benchmark_run_id" pagination={false} dataSource={create.data.results as any[]} columns={[
          { title: '算法', dataIndex: 'algorithm_id' }, { title: '类别', dataIndex: 'category' },
          { title: '网络吞吐 Mbps', dataIndex: 'network_throughput_mbps', render: (v: number) => v.toFixed(2) },
          { title: 'P5 Mbps', dataIndex: 'p5_ue_throughput_mbps', render: (v: number) => v.toFixed(2) },
          { title: '是否满足约束', dataIndex: 'feasible', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '是' : '否'}</Tag> },
          { title: '评价次数', dataIndex: 'evaluations_used' }, { title: '停止原因', dataIndex: 'stop_reason' },
        ]} />
      </Card>}
      {!create.data && latest && <Card title={`最近基准 · ${latest.benchmark_id}`}><Space orientation="vertical"><Text>已保存基准参考；再次运行会生成新的协议化运行记录。</Text><Link to={`/benchmarks/${latest.benchmark_id}`}>查看已保存基准详情</Link></Space></Card>}
      {create.data && <Link to={`/benchmarks/${create.data.benchmark_id}`}>查看已保存基准详情</Link>}
      {create.isError && <Alert type="error" message="基准运行失败" description={create.error instanceof Error ? create.error.message : '未知错误'} />}
    </Space>
  );
}
