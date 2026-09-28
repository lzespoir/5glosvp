import { Alert, App, Button, Collapse, Descriptions, Form, Input, Modal, Result, Select, Space, Tag } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { toApiError } from '../../api/client';
import { useSystemBackends, useSystemScenario, useSystemScenarios } from '../../api/system';
import { useCreateSystemOptimization } from '../../api/systemOptimizations';
import { SystemModelBadge } from '../../components/SystemModelBadge';
import type {
  BenchmarkProtocol,
  SystemObjectiveView,
  SystemOptimizerView,
  SystemParameterView,
} from '../../types/systemOptimization';
import {
  boundsText,
  formatParameter,
  MAX_SYSTEM_CANDIDATES,
  systemOptimizationPath,
  validateCandidates,
} from '../../utils/systemOptimization';

interface Props {
  open: boolean;
  optimizers: SystemOptimizerView[];
  objectives: SystemObjectiveView[];
  parameters: SystemParameterView[];
  protocols: BenchmarkProtocol[];
  onClose: () => void;
}

export function systemOptimizationName(now = dayjs()): string {
  return `Scheduler β Grid Search · ${now.format('YYYY-MM-DD HH:mm:ss')}`;
}

export function CreateSystemOptimizationModal({ open, optimizers, objectives, parameters, protocols, onClose }: Props) {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const mutation = useCreateSystemOptimization();
  const scenarios = useSystemScenarios();
  const backends = useSystemBackends();

  const [name, setName] = useState(systemOptimizationName());
  const [scenarioId, setScenarioId] = useState('');
  const [objectiveId, setObjectiveId] = useState(objectives[0]?.id ?? '');
  const [parameterId, setParameterId] = useState(parameters[0]?.definition.id ?? '');
  const [optimizerId, setOptimizerId] = useState(optimizers[0]?.id ?? '');
  const [protocolId, setProtocolId] = useState(protocols[0]?.protocol_id ?? '');
  const parameter = parameters.find((p) => p.definition.id === parameterId);
  const [candidateText, setCandidateText] = useState((parameter?.recommended_values ?? []).join(', '));
  const [requestError, setRequestError] = useState<{ code: string; message: string } | null>(null);

  const selectedScenarioId = scenarioId || scenarios.data?.[0]?.scenario_id || '';
  const scenarioDetail = useSystemScenario(open && selectedScenarioId ? selectedScenarioId : null);
  const scenarioSummary = scenarios.data?.find((s) => s.scenario_id === selectedScenarioId);
  const backend = backends.data?.find((b) => b.id === scenarioSummary?.backend);
  const optimizer = optimizers.find((o) => o.id === optimizerId);
  const objective = objectives.find((o) => o.id === objectiveId);
  const protocol = protocols.find((p) => p.protocol_id === protocolId);
  const baselineBeta = scenarioDetail.data?.scenario.simulation.scheduler.beta;

  const validation = parameter ? validateCandidates(candidateText, parameter.definition) : null;
  const candidateError =
    validation && 'error' in validation
      ? validation.error
      : validation && validation.values.length > MAX_SYSTEM_CANDIDATES
        ? `最多 ${MAX_SYSTEM_CANDIDATES} 个候选 / At most ${MAX_SYSTEM_CANDIDATES} candidates`
        : null;
  const backendReady = !!backend?.available && backend.capabilities.includes('channel_reuse');
  const canRun =
    !!validation && !candidateError && !!optimizer && !!objective && !!protocol && !!selectedScenarioId
    && backendReady && name.trim().length > 0;

  const close = () => {
    if (mutation.isPending) return;
    setRequestError(null);
    mutation.reset();
    onClose();
  };

  const run = async () => {
    if (!validation || 'error' in validation || !optimizer || !objective || !protocol || !parameter) return;
    setRequestError(null);
    try {
      const opt = await mutation.mutateAsync({
        problem_type: 'system',
        name: name.trim(),
        scenario_id: selectedScenarioId,
        optimizer_id: optimizer.id,
        objective_id: objective.id,
        parameter: { id: parameter.definition.id, candidate_values: validation.values },
        benchmark_protocol_id: protocol.protocol_id,
      });
      message.info('系统级优化已开始 / System optimization started');
      onClose();
      navigate(systemOptimizationPath(opt.optimization_id));
    } catch (err) {
      const apiError = toApiError(err);
      setRequestError({ code: apiError.code, message: `${apiError.messageZh} / ${apiError.messageEn}` });
    }
  };

  const footer = requestError
    ? [
        <Button key="back" onClick={() => setRequestError(null)}>返回 Back</Button>,
        <Button key="close" type="primary" onClick={close}>关闭 Close</Button>,
      ]
    : [
        <Button key="cancel" onClick={close} disabled={mutation.isPending}>取消</Button>,
        <Button key="run" type="primary" onClick={run} disabled={!canRun} loading={mutation.isPending}>
          开始优化 Start Optimization
        </Button>,
      ];

  return (
    <Modal
      open={open}
      title={<span>新建系统级优化 <span className="card-title-en">New System Optimization</span></span>}
      onCancel={close}
      closable={!mutation.isPending}
      footer={footer}
      width={720}
    >
      {requestError ? (
        <Result
          status="error"
          className="run-result"
          title="无法创建优化 Could not start optimization"
          subTitle={
            <Space orientation="vertical" size={2}>
              <code>{requestError.code}</code>
              <span>{requestError.message}</span>
            </Space>
          }
        />
      ) : (
        <Form layout="vertical" requiredMark={false}>
          <Form.Item label="名称 Name">
            <Input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} aria-label="Optimization name" />
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
            <Form.Item label="优化目标 Objective" style={{ flex: 1 }}>
              <Select
                aria-label="Objective"
                value={objectiveId || undefined}
                onChange={setObjectiveId}
                options={objectives.map((o) => ({ value: o.id, label: `${o.id} (${o.direction})` }))}
              />
            </Form.Item>
            <Form.Item label="优化变量 Variable" style={{ flex: 1 }}>
              <Select
                aria-label="Variable"
                value={parameterId || undefined}
                onChange={(id: string) => {
                  setParameterId(id);
                  const next = parameters.find((p) => p.definition.id === id);
                  setCandidateText((next?.recommended_values ?? []).join(', '));
                }}
                options={parameters.map((p) => ({ value: p.definition.id, label: `${p.definition.name_en} (${p.definition.id})` }))}
              />
            </Form.Item>
          </Space>
          <Space size="middle" style={{ display: 'flex' }} align="start">
            <Form.Item label="优化器 Optimizer" style={{ flex: 1 }}>
              <Select
                aria-label="Optimizer"
                value={optimizerId || undefined}
                onChange={setOptimizerId}
                options={optimizers.map((o) => ({ value: o.id, label: `${o.name_zh} ${o.name_en}` }))}
              />
            </Form.Item>
            <Form.Item label="评估协议 Benchmark Protocol" style={{ flex: 1 }}>
              <Select
                aria-label="Benchmark protocol"
                value={protocolId || undefined}
                onChange={setProtocolId}
                options={protocols.map((p) => ({ value: p.protocol_id, label: `${p.protocol_id} v${p.version}` }))}
              />
            </Form.Item>
          </Space>
          {parameter && (
            <Form.Item
              label={
                <Space size={6}>
                  候选值 Candidate Values ({parameter.definition.id})
                  <Tag>范围 Range {boundsText(parameter.definition)}</Tag>
                </Space>
              }
              validateStatus={candidateError ? 'error' : undefined}
              help={
                candidateError
                ?? `基线 Baseline β = ${formatParameter(baselineBeta)}（场景配置，单独评估）· 最多 ${MAX_SYSTEM_CANDIDATES} 个候选`
              }
            >
              <Input aria-label="Candidate values" value={candidateText} onChange={(e) => setCandidateText(e.target.value)} />
            </Form.Item>
          )}
          <Collapse
            size="small"
            items={[
              {
                key: 'advanced',
                label: '高级设置 Advanced Settings',
                children: (
                  <>
                    <Descriptions column={1} size="small" bordered>
                      <Descriptions.Item label="后端 Backend">
                        {backend ? `${backend.name_en}${backend.version ? ` v${backend.version}` : ''}` : scenarioSummary?.backend ?? '—'}{' '}
                        {backend && <SystemModelBadge modelType={backend.model_type} />}
                      </Descriptions.Item>
                      <Descriptions.Item label="协议 Protocol">
                        {protocol
                          ? `${protocol.simulation_slots} slots · warm-up ${protocol.warmup_slots} · repeats ${protocol.num_repeats} · ${protocol.aggregation_method}`
                          : '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="随机种子 Seed">
                        {scenarioSummary?.seed ?? '—'} <span className="muted">（固定 Fixed · {protocol?.seed_policy}）</span>
                      </Descriptions.Item>
                      <Descriptions.Item label="推荐值来源 Search Space Source">
                        {parameter?.recommended_values_source ?? '—'}
                      </Descriptions.Item>
                    </Descriptions>
                    <div className="section">
                      <strong>算法设置 Algorithm Settings</strong>
                      <div className="muted">
                        {optimizer && optimizer.hyperparameters.length > 0
                          ? optimizer.hyperparameters.map((h) => `${h.name_en} (${h.id})`).join(', ')
                          : 'Grid Search 无算法超参数：只遍历上面列出的候选值。No hyperparameters.'}
                      </div>
                    </div>
                  </>
                ),
              },
            ]}
          />
          {backends.data && !backendReady && (
            <Alert
              type="error"
              showIcon
              className="section"
              title="仿真后端当前不可用或不支持信道复用，无法运行系统级优化。Backend unavailable or lacks channel_reuse."
              description={backend?.reason ?? undefined}
            />
          )}
        </Form>
      )}
    </Modal>
  );
}
