import { ArrowLeftOutlined, LinkOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Descriptions, Empty, Space, Spin, Statistic, Table, Tag, Tabs, Typography } from 'antd';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useBenchmarkDetail } from '../../api/benchmarks';

const { Title, Text } = Typography;

function runtimeColumns() {
  return [
    { title: 'Total wall time (includes simulator evaluations)', dataIndex: ['runtime', 'total_wall_time'], render: (v: number) => `${Number(v ?? 0).toFixed(3)} s` },
    { title: 'Simulator evaluation time', dataIndex: ['runtime', 'simulation_evaluation_time'], render: (v: number) => `${Number(v ?? 0).toFixed(3)} s` },
    { title: 'Optimizer overhead', dataIndex: ['runtime', 'optimizer_overhead_time'], render: (v: number) => `${Number(v ?? 0).toFixed(3)} s` },
  ];
}

export function BenchmarkDetailPage() {
  const { benchmarkId = '', section = 'overview' } = useParams();
  const navigate = useNavigate();
  const detail = useBenchmarkDetail(benchmarkId);
  if (detail.isLoading) return <Spin description="Loading persisted benchmark evidence…" />;
  if (detail.isError || !detail.data) return <Empty description="Benchmark evidence unavailable" />;
  const d = detail.data;
  const benchmark = d.benchmark;
  const sectionKey = ['overview', 'comparison', 'convergence', 'runs', 'evidence'].includes(section) ? section : 'overview';
  const runLink = (id: string) => <Link to={`/benchmarks/${benchmarkId}/runs/${id}`}>{id}</Link>;

  const overview = <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
    <Alert type="info" showIcon title="Persisted benchmark reference" description="This view is loaded from the saved benchmark reference and does not rerun propagation or create frontend data." />
    <Descriptions bordered column={{ xs: 1, md: 2 }}>
      <Descriptions.Item label="Benchmark">{benchmark.benchmark_id}</Descriptions.Item>
      <Descriptions.Item label="Status">{benchmark.status}</Descriptions.Item>
      <Descriptions.Item label="Problem">{benchmark.problem_id}</Descriptions.Item>
      <Descriptions.Item label="Scenario">{benchmark.scenario_set?.join(', ')}</Descriptions.Item>
      <Descriptions.Item label="Protocol">{benchmark.protocol_id}</Descriptions.Item>
      <Descriptions.Item label="Protocol hash"><Text code>{benchmark.protocol_hash}</Text></Descriptions.Item>
      <Descriptions.Item label="Channel artifact"><Text code>{d.provenance.channel_realization_id}</Text></Descriptions.Item>
      <Descriptions.Item label="Comparison"><Tag color={d.evidence.comparison_eligible ? 'green' : 'red'}>{d.evidence.comparison_eligible ? 'ELIGIBLE' : 'NOT ELIGIBLE'}</Tag></Descriptions.Item>
    </Descriptions>
    <Card title="Shared evaluation context">
      <Space orientation="vertical" size="small">
        <Text>Objective: {d.protocol.objective?.id} ({d.protocol.objective?.direction})</Text>
        <Text>Constraint: P5 {d.protocol.constraints?.[0]?.operator} {d.protocol.constraints?.[0]?.value}</Text>
        <Text>Evaluation budget: {d.protocol.evaluation_budget}</Text>
        <Text>Traffic: {d.protocol.traffic_realization_policy}</Text>
        <Text>Channel policy: {d.protocol.channel_realization_policy}</Text>
      </Space>
    </Card>
  </Space>;

  const comparison = <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
    <Alert type="success" showIcon title="Comparison eligible: YES" description="The verifier found the same problem, scenario, baseline, frozen channel artifact/hash, objective, constraints, KPI versions and evaluation budget." />
    <Table rowKey="benchmark_run_id" pagination={false} dataSource={d.comparison} columns={[
      { title: 'Algorithm', dataIndex: 'algorithm_id' },
      { title: 'Run', dataIndex: 'benchmark_run_id', render: runLink },
      { title: 'Network Mbps', dataIndex: 'network_throughput_mbps', render: (v: number) => Number(v).toFixed(6) },
      { title: 'P5 Mbps', dataIndex: 'p5_ue_throughput_mbps', render: (v: number) => Number(v).toFixed(6) },
      { title: 'Feasible', dataIndex: 'feasible', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{String(v)}</Tag> },
      { title: 'Evaluations', dataIndex: 'evaluations_used' },
      { title: 'Total wall time', ...runtimeColumns()[0] },
      { title: 'Stop reason', dataIndex: 'stop_reason' },
    ]} />
    <Text type="secondary">Runtime wording is intentionally total wall time; it includes simulator evaluations and must not be interpreted as pure algorithm compute time.</Text>
  </Space>;

  const convergence = <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
    {d.runs.map((run) => <Card key={run.benchmark_run_id} title={runLink(run.benchmark_run_id)}>
      <Table rowKey="evaluation_index" size="small" pagination={false} dataSource={d.convergence[run.benchmark_run_id] ?? []} columns={[
        { title: 'Evaluation', dataIndex: 'evaluation_index' },
        { title: 'Current objective', dataIndex: 'current_objective', render: (v: number | null) => v == null ? 'infeasible' : Number(v).toFixed(6) },
        { title: 'Best feasible objective', dataIndex: 'best_feasible_objective', render: (v: number | null) => v == null ? '—' : Number(v).toFixed(6) },
        { title: 'Feasible', dataIndex: 'current_feasible', render: (v: boolean) => String(v) },
        { title: 'Elapsed simulator time', dataIndex: 'elapsed_time', render: (v: number) => `${Number(v).toFixed(3)} s` },
      ]} />
    </Card>)}
  </Space>;

  const runs = <Table rowKey="benchmark_run_id" pagination={false} dataSource={d.runs} columns={[
    { title: 'Run ID', dataIndex: 'benchmark_run_id', render: runLink },
    { title: 'Algorithm', dataIndex: 'algorithm_id' },
    { title: 'Status', dataIndex: 'status' },
    { title: 'Evaluations', dataIndex: 'evaluations_used' },
    { title: 'Feasible', dataIndex: 'feasible', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{String(v)}</Tag> },
    { title: 'Total wall time (includes simulator)', ...runtimeColumns()[0] },
    { title: 'Optimization ID', dataIndex: 'optimization_id' },
  ]} />;

  const env = d.closure?.runtime_environment ?? d.provenance.runtime_environment;
  const evidence = <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
    <Card title="Verification">
      <Descriptions column={1} size="small">
        <Descriptions.Item label="Independent verifier">{d.verification.status}</Descriptions.Item>
        <Descriptions.Item label="Comparable">{String(d.verification.comparable)}</Descriptions.Item>
        <Descriptions.Item label="Tamper tests">{d.verification.tamper_tests}</Descriptions.Item>
        <Descriptions.Item label="Evidence level">{d.evidence.evidence_level}</Descriptions.Item>
        <Descriptions.Item label="Acceptance eligible">{String(d.evidence.acceptance_eligible)}</Descriptions.Item>
      </Descriptions>
    </Card>
    <Card title="Frozen channel provenance">
      <Descriptions column={1} size="small">
        <Descriptions.Item label="Artifact ID">{d.provenance.channel_realization_id}</Descriptions.Item>
        <Descriptions.Item label="Artifact SHA-256"><Text code>{d.provenance.channel_hash}</Text></Descriptions.Item>
        <Descriptions.Item label="Policy">Same artifact ID + same artifact hash; seed alone is insufficient.</Descriptions.Item>
      </Descriptions>
    </Card>
    <Card title="Runtime environment provenance">
      {env ? <Descriptions column={{ xs: 1, md: 2 }} size="small">
        {Object.entries(env).map(([key, value]) => <Descriptions.Item key={key} label={key}>{value == null ? 'null' : String(value)}</Descriptions.Item>)}
      </Descriptions> : <Text type="secondary">No closure environment record is available.</Text>}
    </Card>
    <Card title="Runtime semantics">
      <Text>{d.closure?.runtime_semantics?.total_wall_time_includes ?? 'Total wall time includes simulator evaluations; see persisted runtime fields for the split.'}</Text>
    </Card>
    {d.closure?.td_009 && <Card title="TD-009 · Deterministic Replay of Sionna RT"><Text>{d.closure.td_009.policy}</Text></Card>}
  </Space>;

  const content = { overview, comparison, convergence, runs, evidence }[sectionKey as 'overview' | 'comparison' | 'convergence' | 'runs' | 'evidence'];
  return <Space orientation="vertical" size="large" style={{ width: '100%' }}>
    <Space><Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/benchmarks')}>Back to Benchmark Center</Button><Title level={2} style={{ margin: 0 }}>{benchmark.name}</Title></Space>
    <Tabs activeKey={sectionKey} onChange={(key) => navigate(`/benchmarks/${benchmarkId}/${key}`)} items={[
      { key: 'overview', label: 'Overview' }, { key: 'comparison', label: 'Comparison' }, { key: 'convergence', label: 'Convergence' }, { key: 'runs', label: 'Runs' }, { key: 'evidence', label: 'Evidence' },
    ]} />
    {content}
  </Space>;
}

export function BenchmarkRunDetailPage() {
  const { benchmarkId = '', runId = '' } = useParams();
  const navigate = useNavigate();
  const detail = useBenchmarkDetail(benchmarkId);
  if (detail.isLoading) return <Spin description="Loading persisted run…" />;
  if (detail.isError || !detail.data) return <Empty description="Benchmark run unavailable" />;
  const run = detail.data.runs.find((item) => item.benchmark_run_id === runId);
  if (!run) return <Empty description="Benchmark run not found" />;
  const best = run.best_candidate ?? {};
  return <Space orientation="vertical" size="large" style={{ width: '100%' }}>
    <Space><Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/benchmarks/${benchmarkId}/runs`)}>Back to Runs</Button><Title level={2} style={{ margin: 0 }}>Optimization Run</Title></Space>
    <Alert type="info" showIcon title={run.benchmark_run_id} description="Run detail is read from persisted benchmark evidence." />
    <Descriptions bordered column={{ xs: 1, md: 2 }}>
      <Descriptions.Item label="Algorithm">{run.algorithm_id} v{run.algorithm_version}</Descriptions.Item>
      <Descriptions.Item label="Status">{run.status}</Descriptions.Item>
      <Descriptions.Item label="Optimization ID">{run.optimization_id}</Descriptions.Item>
      <Descriptions.Item label="Seed">{run.seed}</Descriptions.Item>
      <Descriptions.Item label="Evaluations used">{run.evaluations_used}</Descriptions.Item>
      <Descriptions.Item label="Feasible"><Tag color={run.feasible ? 'green' : 'red'}>{String(run.feasible)}</Tag></Descriptions.Item>
      <Descriptions.Item label="Stop reason">{run.stop_reason}</Descriptions.Item>
      <Descriptions.Item label="Total wall time (includes simulator evaluations)">{Number(run.runtime?.total_wall_time ?? 0).toFixed(3)} s</Descriptions.Item>
    </Descriptions>
    <Card title="Best candidate KPI">
      <Space size="large"><Statistic title="Network throughput (Mbps)" value={best.network_throughput_mbps} precision={6} /><Statistic title="Average UE throughput (Mbps)" value={best.average_ue_throughput_mbps} precision={6} /><Statistic title="P5 UE throughput (Mbps)" value={best.p5_ue_throughput_mbps} precision={6} /></Space>
    </Card>
    <Card title="Runtime split" extra={<Text type="secondary">Total includes simulator evaluations</Text>}><Descriptions column={1} size="small">
      <Descriptions.Item label="Total wall time">{Number(run.runtime?.total_wall_time ?? 0).toFixed(6)} s</Descriptions.Item>
      <Descriptions.Item label="Simulator evaluation time">{Number(run.runtime?.simulation_evaluation_time ?? 0).toFixed(6)} s</Descriptions.Item>
      <Descriptions.Item label="Optimizer overhead">{Number(run.runtime?.optimizer_overhead_time ?? 0).toFixed(6)} s</Descriptions.Item>
    </Descriptions></Card>
    <Card title="Verification"><Descriptions column={1} size="small"><Descriptions.Item label="Protocol hash"><Text code>{run.verification?.protocol_hash}</Text></Descriptions.Item><Descriptions.Item label="Channel hash"><Text code>{run.verification?.channel_hash}</Text></Descriptions.Item><Descriptions.Item label="Independent verification">{String(run.verification?.independent_verified)}</Descriptions.Item></Descriptions></Card>
    <Button icon={<LinkOutlined />} onClick={() => navigate(`/benchmarks/${benchmarkId}/convergence`)}>View convergence</Button>
  </Space>;
}
