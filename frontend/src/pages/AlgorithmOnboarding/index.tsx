import { CheckCircleOutlined, CloudUploadOutlined, ExperimentOutlined, SafetyOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Descriptions, Divider, Input, InputNumber, Result, Row, Space, Spin, Steps, Tag, Typography } from 'antd';
import { useMemo, useState } from 'react';

import { API_BASE_URL, resolveApiUrl } from '../../api/client';
import {
  cloneExternalExperiment,
  createExternalExperiment,
  registerPackage,
  smokeTestPackage,
  useExternalExperiment,
  validatePackage,
} from '../../api/algorithmPackages';
import type { PackageCheck } from '../../api/algorithmPackages';
import { PageHeader } from '../../components/PageHeader';

const DEFAULT_PATH = 'examples/algorithm_packages/example_external_optimizer';
const DEFAULT_SCENARIO = 'MULTICELL-DEMO-001';

function StatusTag({ value }: { value?: string }) {
  const good = value === 'PASS' || value === 'VALIDATED' || value === 'REGISTERED' || value === 'completed';
  return <Tag color={good ? 'success' : value === 'FAILED' || value === 'failed' ? 'error' : 'processing'}>{value || 'not started'}</Tag>;
}

function ErrorSummary({ check }: { check?: PackageCheck | null }) {
  if (!check || !check.errors?.length) return null;
  return <Alert type="error" showIcon title={`${check.stage || 'Package'} failed`} description={check.errors.map((error) => `${error.code || 'ERROR'}: ${error.message || 'unknown error'}`).join(' · ')} />;
}

export function AlgorithmOnboardingPage() {
  const [path, setPath] = useState(DEFAULT_PATH);
  const [validation, setValidation] = useState<PackageCheck | null>(null);
  const [smoke, setSmoke] = useState<PackageCheck | null>(null);
  const [registered, setRegistered] = useState<any | null>(null);
  const [parameters, setParameters] = useState<Record<string, any>>({ seed: 20260929, candidate_offset: 1 });
  const [budget, setBudget] = useState(8);
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const run = useExternalExperiment(runId);
  const manifest = registered?.manifest as Record<string, any> | undefined;
  const parameterSchema = (manifest?.parameters || {}) as Record<string, Record<string, any>>;
  const runData = run.data;
  const runFinished = ['completed', 'failed', 'time_limit_exceeded'].includes(runData?.status || '');

  const step = useMemo(() => {
    if (runData) return runFinished ? 7 : 6;
    if (registered) return 5;
    if (smoke?.status === 'PASS') return 3;
    if (validation?.status === 'VALIDATED') return 2;
    return 0;
  }, [registered, runData, runFinished, smoke, validation]);

  async function perform(name: string, action: () => Promise<any>, setter?: (value: any) => void) {
    setBusy(name);
    try {
      const result = await action();
      setter?.(result);
      return result;
    } finally {
      setBusy(null);
    }
  }

  async function handleRegister() {
    const result = await perform('register', () => registerPackage(path));
    setRegistered(result);
    if (result.manifest?.parameters) {
      const defaults = Object.fromEntries(Object.entries(result.manifest.parameters).map(([key, value]: [string, any]) => [key, value.default]));
      setParameters(defaults);
    }
  }

  async function handleRun() {
    if (!registered?.package_id) return;
    const result = await perform('run', () => createExternalExperiment({
      package_id: registered.package_id,
      scenario_id: DEFAULT_SCENARIO,
      parameters,
      evaluation_budget: budget,
      time_limit_seconds: null,
    }));
    setRunId(result.run_id);
  }

  async function handleClone() {
    if (!runData) return;
    const result = await perform('clone', () => cloneExternalExperiment(runData.run_id, runData.parameters));
    setRunId(result.run_id);
  }

  return (
    <>
      <PageHeader
        titleZh="外部算法接入"
        titleEn="External Algorithm Onboarding"
        subtitle={<span>Trusted Python V0.1 · API base <code>{API_BASE_URL}</code></span>}
        extra={<Button icon={<CloudUploadOutlined />} onClick={() => setRegistered(null)}>新建接入 New package</Button>}
      />
      <Alert
        className="section-bottom"
        type="warning"
        showIcon
        icon={<SafetyOutlined />}
        title="当前版本只允许工作区内的受信任本地 Python 包"
        description="不会访问 Git/PyPI/Docker/Notebook/远程 URL，不会自动安装依赖，也尚未提供恶意代码隔离。外部算法只能提出候选；平台负责仿真评价、KPI、约束、trace 和证据。"
      />

      <Card title="Package → Validate → Smoke Test → Register → Configure → Run → Observe → Compare → Export" className="section-bottom">
        <Steps current={step} items={[
          { title: 'Package', content: 'Local directory' },
          { title: 'Validate', content: <StatusTag value={validation?.status} /> },
          { title: 'Smoke Test', content: <StatusTag value={smoke?.status} /> },
          { title: 'Register', content: <StatusTag value={registered?.status} /> },
          { title: 'Configure', content: 'Experiment' },
          { title: 'Run', content: 'Platform lifecycle' },
          { title: 'Observe', content: 'Trace / KPI' },
          { title: 'Export', content: 'Evidence bundle' },
        ]} />
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card title="1. Package and validation">
            <Space orientation="vertical" style={{ width: '100%' }} size="middle">
              <Space.Compact style={{ width: '100%' }}>
                <Typography.Text style={{ padding: '5px 11px', border: '1px solid #d9d9d9', background: '#fafafa' }}>Local path</Typography.Text>
                <Input value={path} onChange={(event) => setPath(event.target.value)} />
              </Space.Compact>
              <Space wrap>
                <Button loading={busy === 'validate'} onClick={() => perform('validate', () => validatePackage(path), setValidation)}>Validate</Button>
                <Button loading={busy === 'smoke'} disabled={validation?.status !== 'VALIDATED'} onClick={() => perform('smoke', () => smokeTestPackage(path), setSmoke)}>Smoke Test</Button>
                <Button type="primary" loading={busy === 'register'} disabled={smoke?.status !== 'PASS'} onClick={handleRegister}>Register</Button>
              </Space>
              <ErrorSummary check={validation} />
              <ErrorSummary check={smoke} />
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="Validation"><StatusTag value={validation?.status} /></Descriptions.Item>
                <Descriptions.Item label="Smoke"><StatusTag value={smoke?.status} /></Descriptions.Item>
                <Descriptions.Item label="Registration"><StatusTag value={registered?.status} /></Descriptions.Item>
                <Descriptions.Item label="SDK">{registered?.manifest?.sdk?.version || '—'}</Descriptions.Item>
              </Descriptions>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card title="2. Registered package detail">
            {!registered ? <Typography.Paragraph type="secondary">通过 Validate、Smoke Test 后注册，平台会保留 manifest/source/package identity。</Typography.Paragraph> : (
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="Algorithm">{registered.algorithm_id} v{registered.algorithm_version}</Descriptions.Item>
                <Descriptions.Item label="Provider">{registered.manifest?.algorithm?.provider}</Descriptions.Item>
                <Descriptions.Item label="Category"><Tag color="blue">{registered.manifest?.algorithm?.category}</Tag></Descriptions.Item>
                <Descriptions.Item label="Origin">{registered.manifest?.implementation_origin}</Descriptions.Item>
                <Descriptions.Item label="Package hash"><code>{registered.package_hash}</code></Descriptions.Item>
                <Descriptions.Item label="Manifest hash"><code>{registered.manifest_hash}</code></Descriptions.Item>
                <Descriptions.Item label="Source hash"><code>{registered.source_hash}</code></Descriptions.Item>
                <Descriptions.Item label="Compatibility">{(registered.manifest?.compatibility?.problem_types || []).join(', ')} / {(registered.manifest?.compatibility?.parameter_types || []).join(', ')}</Descriptions.Item>
              </Descriptions>
            )}
          </Card>
        </Col>
      </Row>

      {registered && (
        <Card title="3. Experiment Workspace" className="section">
          <Row gutter={[24, 16]}>
            <Col xs={24} lg={9}>
              <Typography.Title level={5}>Dynamic parameters</Typography.Title>
              <Space orientation="vertical" style={{ width: '100%' }}>
                {Object.entries(parameterSchema).map(([name, spec]) => (
                  <div key={name}>
                    <Typography.Text strong>{name}</Typography.Text>
                    {spec.type === 'integer' || spec.type === 'float' ? (
                      <InputNumber style={{ width: '100%' }} value={parameters[name]} min={spec.minimum} max={spec.maximum} onChange={(value) => setParameters((old) => ({ ...old, [name]: value }))} />
                    ) : <Input value={parameters[name]} onChange={(event) => setParameters((old) => ({ ...old, [name]: event.target.value }))} />}
                  </div>
                ))}
                <div>
                  <Typography.Text strong>Evaluation budget</Typography.Text>
                  <InputNumber style={{ width: '100%' }} min={1} max={12} value={budget} onChange={(value) => setBudget(value || 8)} />
                </div>
              </Space>
            </Col>
            <Col xs={24} lg={15}>
              <Typography.Title level={5}>Review</Typography.Title>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Problem">USER_ASSOCIATION</Descriptions.Item>
                <Descriptions.Item label="Scenario">{DEFAULT_SCENARIO}</Descriptions.Item>
                <Descriptions.Item label="Objective">NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1</Descriptions.Item>
                <Descriptions.Item label="Constraint">P5 floor held by platform evaluator</Descriptions.Item>
                <Descriptions.Item label="Data source">Simulation · Day 8 frozen channel</Descriptions.Item>
                <Descriptions.Item label="Parameters"><code>{JSON.stringify(parameters)}</code></Descriptions.Item>
              </Descriptions>
              <Divider />
              <Space wrap>
                <Button type="primary" icon={<ExperimentOutlined />} loading={busy === 'run'} onClick={handleRun}>Run experiment</Button>
                {runData && <Button onClick={handleClone} loading={busy === 'clone'}>Clone</Button>}
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {runId && (
        <Card title="4. Running / Logs / KPI / Evidence" className="section">
          {!runData ? <Spin description="Loading run…" /> : (
            <>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Run"><code>{runData.run_id}</code></Descriptions.Item>
                <Descriptions.Item label="Status"><StatusTag value={runData.status} /> {runData.stage}</Descriptions.Item>
                <Descriptions.Item label="Evaluations">{runData.evaluations_used ?? '—'} / {runData.evaluation_budget}</Descriptions.Item>
                <Descriptions.Item label="Frozen channel"><code>{runData.channel_hash || 'loading'}</code></Descriptions.Item>
                <Descriptions.Item label="Best KPI">{runData.best_candidate ? `${runData.best_candidate.network_throughput_mbps} Mbps network throughput · P5 ${runData.best_candidate.p5_ue_throughput_mbps} Mbps` : 'running'}</Descriptions.Item>
              </Descriptions>
              {runData.status === 'completed' && (
                <Result
                  status="success"
                  icon={<CheckCircleOutlined />}
                  title="Platform run completed"
                  subTitle="This proves onboarding and integration evidence; it is not a correctness or paper-reproduction claim."
                  extra={<Space wrap>
                    {runData.benchmark_id && <Button href={`/benchmarks/${runData.benchmark_id}`}>Open Day 10 Benchmark</Button>}
                    {runData.export_bundle && <Button type="primary" href={resolveApiUrl(`/algorithm-experiments/${runData.run_id}/export`)}>Export evidence bundle</Button>}
                  </Space>}
                />
              )}
              {runData.status === 'failed' && <Alert type="error" showIcon title="Run failed" description={runData.error?.message || 'See logs and structured error.'} />}
            </>
          )}
        </Card>
      )}
    </>
  );
}
