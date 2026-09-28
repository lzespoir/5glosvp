import { LoadingOutlined } from '@ant-design/icons';
import { Alert, App, Button, Descriptions, Form, Input, Modal, Result, Select, Space, Spin, Tag } from 'antd';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useBackends } from '../../api/backends';
import { toApiError } from '../../api/client';
import { useCreateOptimization } from '../../api/optimizations';
import { useScenario, useScenarios } from '../../api/scenarios';
import { ProvenanceTag } from '../../components/ProvenanceTag';
import type { ObjectiveView, OptimizationResponse, OptimizerView } from '../../types/optimization';
import { formatPower, parseCandidateValues, TX_POWER } from '../../utils/optimization';

type Outcome =
  | { kind: 'failed'; optimization: OptimizationResponse }
  | { kind: 'request_error'; code: string; message: string };

interface Props {
  open: boolean;
  optimizers: OptimizerView[];
  objectives: ObjectiveView[];
  onClose: () => void;
}

export function optimizationName(now = dayjs()): string {
  return `TX Power Grid Search · ${now.format('YYYY-MM-DD HH:mm:ss')}`;
}

export function validateCandidates(text: string, maxCandidates: number): string | null {
  const values = parseCandidateValues(text);
  if (!values) return '请输入数值，以逗号分隔 / Enter comma-separated numbers';
  if (new Set(values).size !== values.length) return '候选值不能重复 / Candidate values must be unique';
  if (values.length > maxCandidates) return `候选数量不能超过 ${maxCandidates} / At most ${maxCandidates} candidates`;
  return null;
}

export function CreateOptimizationModal({ open, optimizers, objectives, onClose }: Props) {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const mutation = useCreateOptimization();
  const scenarios = useScenarios();
  const backends = useBackends();

  const defaultOptimizer = optimizers.find((o) => o.available) ?? optimizers[0];
  const [optimizerId, setOptimizerId] = useState(defaultOptimizer?.id ?? '');
  const [objectiveId, setObjectiveId] = useState(objectives[0]?.id ?? '');
  const [scenarioId, setScenarioId] = useState('');
  const optimizer = optimizers.find((o) => o.id === optimizerId);
  const objective = objectives.find((o) => o.id === objectiveId);
  const recommended = optimizer?.recommended_parameter_space[TX_POWER] ?? [];
  const [candidateText, setCandidateText] = useState(recommended.join(', '));
  const [name, setName] = useState(optimizationName());
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  const selectedScenarioId = scenarioId || scenarios.data?.[0]?.scenario_id || '';
  const scenarioDetail = useScenario(selectedScenarioId, open);
  const scenarioSummary = scenarios.data?.find((s) => s.scenario_id === selectedScenarioId);
  const backend = backends.data?.find((b) => b.id === scenarioSummary?.backend);
  const baselinePowers = useMemo(
    () => (scenarioDetail.data?.transmitters ?? []).map((t) => t.power_dbm),
    [scenarioDetail.data],
  );

  const maxCandidates = optimizer?.max_candidates ?? 10;
  const candidateError = validateCandidates(candidateText, maxCandidates);
  const running = mutation.isPending;
  const canRun =
    !candidateError && !!optimizer?.available && !!objective && !!selectedScenarioId && !!backend?.available && name.trim().length > 0;

  const close = () => {
    if (running) return;
    setOutcome(null);
    mutation.reset();
    onClose();
  };

  const run = async () => {
    const values = parseCandidateValues(candidateText);
    if (!values || !optimizer || !objective) return;
    setOutcome(null);
    try {
      const opt = await mutation.mutateAsync({
        name: name.trim(),
        scenario_id: selectedScenarioId,
        optimizer_id: optimizer.id,
        objective_id: objective.id,
        parameter_space: { tx_power_dbm: values },
      });
      if (opt.status === 'failed') {
        setOutcome({ kind: 'failed', optimization: opt });
      } else {
        message.success('优化实验完成 / Optimization completed');
        onClose();
        navigate(`/optimizations/${opt.optimization_id}`);
      }
    } catch (err) {
      const apiError = toApiError(err);
      setOutcome({ kind: 'request_error', code: apiError.code, message: `${apiError.messageZh} / ${apiError.messageEn}` });
    }
  };

  const failed = outcome?.kind === 'failed' ? outcome.optimization : null;

  let footer;
  if (running) {
    footer = [
      <Button key="running" type="primary" loading disabled>
        运行中... Running...
      </Button>,
    ];
  } else if (failed) {
    footer = [
      <Button key="close" onClick={close}>关闭 Close</Button>,
      <Button key="detail" type="primary" onClick={() => { close(); navigate(`/optimizations/${failed.optimization_id}`); }}>
        查看优化详情 View Optimization
      </Button>,
    ];
  } else {
    footer = [
      <Button key="cancel" onClick={close}>取消</Button>,
      <Button key="run" type="primary" onClick={run} disabled={!canRun}>
        运行优化 Run Optimization
      </Button>,
    ];
  }

  return (
    <Modal
      open={open}
      title={<span>新建优化实验 <span className="card-title-en">New Optimization Run</span></span>}
      onCancel={close}
      closable={!running}
      mask={{ closable: !running }}
      keyboard={!running}
      footer={footer}
      width={640}
    >
      {running ? (
        <div className="run-progress">
          <Spin indicator={<LoadingOutlined spin />} size="large" />
          <div className="run-progress__title">正在执行参数搜索</div>
          <div className="muted">Running parameter search. 每个候选都会运行一次真实仿真，请勿关闭页面。</div>
        </div>
      ) : outcome ? (
        <Result
          status="error"
          className="run-result"
          title="优化实验失败 Optimization Failed"
          subTitle={
            outcome.kind === 'failed' ? (
              <Space orientation="vertical" size={2}>
                <span>优化编号 <code>{outcome.optimization.optimization_id}</code></span>
                {outcome.optimization.error ? (
                  <>
                    <code>{outcome.optimization.error.code}</code>
                    <span>{outcome.optimization.error.message}</span>
                    {outcome.optimization.error.failed_candidate_id && (
                      <span>失败候选 Failed candidate: <code>{outcome.optimization.error.failed_candidate_id}</code></span>
                    )}
                  </>
                ) : (
                  <span>后端未返回错误详情 / No error detail</span>
                )}
              </Space>
            ) : (
              <Space orientation="vertical" size={2}>
                <code>{outcome.code}</code>
                <span>{outcome.message}</span>
              </Space>
            )
          }
        />
      ) : (
        <Form layout="vertical" requiredMark={false}>
          <Form.Item label="名称 Name">
            <Input value={name} maxLength={200} onChange={(e) => setName(e.target.value)} aria-label="Optimization name" />
          </Form.Item>
          <Form.Item label="场景 Scenario">
            <Select
              aria-label="Scenario"
              value={selectedScenarioId || undefined}
              loading={scenarios.isLoading}
              onChange={setScenarioId}
              options={(scenarios.data ?? []).map((s) => ({ value: s.scenario_id, label: `${s.name_zh} · ${s.scenario_id}` }))}
            />
          </Form.Item>
          <Space size="middle" style={{ display: 'flex' }} align="start">
            <Form.Item label="优化器 Optimizer" style={{ flex: 1 }}>
              <Select
                aria-label="Optimizer"
                value={optimizerId || undefined}
                onChange={(id: string) => {
                  setOptimizerId(id);
                  const next = optimizers.find((o) => o.id === id);
                  setCandidateText((next?.recommended_parameter_space[TX_POWER] ?? []).join(', '));
                }}
                options={optimizers.map((o) => ({ value: o.id, label: `${o.name_zh} ${o.name_en}`, disabled: !o.available }))}
              />
            </Form.Item>
            <Form.Item label="优化目标 Objective" style={{ flex: 1 }}>
              <Select
                aria-label="Objective"
                value={objectiveId || undefined}
                onChange={setObjectiveId}
                options={objectives.map((o) => ({ value: o.id, label: `${o.name_en} v${o.version}` }))}
              />
            </Form.Item>
          </Space>
          <Descriptions column={1} size="small" bordered className="section-bottom">
            <Descriptions.Item label="优化参数 Parameter">发射功率 TX Power (dBm)</Descriptions.Item>
            <Descriptions.Item label="基线 Baseline">
              场景原始配置 {baselinePowers.length > 0 ? baselinePowers.map((p) => formatPower(p ?? null)).join(' / ') : '—'}
              <span className="muted">（独立运行 · Runs independently）</span>
            </Descriptions.Item>
            <Descriptions.Item label="后端 Backend">
              {backend ? `${backend.name_zh}${backend.version ? ` v${backend.version}` : ''}` : scenarioSummary?.backend ?? '—'}{' '}
              <ProvenanceTag sourceType={backend?.source_type} />
            </Descriptions.Item>
          </Descriptions>
          <Form.Item
            label={
              <Space size={6}>
                候选值 Candidate Values (dBm)
                <Tag color="gold">演示搜索空间 Demo Search Space · [A] Assumption</Tag>
              </Space>
            }
            validateStatus={candidateError ? 'error' : undefined}
            help={candidateError ?? `最多 ${maxCandidates} 个候选，全部使用相同随机种子。At most ${maxCandidates} candidates, same seed.`}
          >
            <Input
              aria-label="Candidate values"
              value={candidateText}
              onChange={(e) => setCandidateText(e.target.value)}
            />
          </Form.Item>
          {!backend?.available && backends.data && (
            <Alert
              type="error"
              showIcon
              title="仿真后端当前不可用，无法运行优化。Simulation backend unavailable."
              description={backend?.reason ?? undefined}
            />
          )}
        </Form>
      )}
    </Modal>
  );
}
