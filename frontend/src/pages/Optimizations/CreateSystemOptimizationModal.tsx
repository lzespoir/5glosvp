import { Alert, App, Button, Col, Collapse, Descriptions, Form, Input, Modal, Result, Row, Select, Space } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAlgorithm, useAlgorithmValidation } from '../../api/algorithms';
import { toApiError } from '../../api/client';
import { useSystemBackends, useSystemScenario, useSystemScenarios } from '../../api/system';
import { useCreateSystemOptimization } from '../../api/systemOptimizations';
import { SystemModelBadge } from '../../components/SystemModelBadge';
import type { AlgorithmSummary, AlgorithmValidateRequest, HyperparameterValue, ParameterSpec } from '../../types/algorithm';
import type { BenchmarkProtocol, SystemObjectiveView, SystemParameterView } from '../../types/systemOptimization';
import {
  DEFAULT_EVALUATION_BUDGET,
  defaultHyperparameters,
  editableParameterType,
  GRID_SEARCH_ID,
  hyperparameterError,
} from '../../utils/algorithm';
import { MAX_SYSTEM_CANDIDATES, systemOptimizationPath, validateCandidates } from '../../utils/systemOptimization';
import { AlgorithmTags } from '../Algorithms/AlgorithmTags';
import { AlgorithmSettings, type SettingsMode } from './AlgorithmSettings';
import { CompatibilityFeedback } from './CompatibilityFeedback';
import { type ContinuousRange, continuousRangeError, ParameterSpaceEditor } from './ParameterSpaceEditor';

interface Props {
  open: boolean;
  algorithms: AlgorithmSummary[];
  objectives: SystemObjectiveView[];
  parameters: SystemParameterView[];
  protocols: BenchmarkProtocol[];
  onClose: () => void;
}

const VALIDATE_DEBOUNCE_MS = 300;

export function systemOptimizationName(algorithmName = 'Grid Search', now = dayjs()): string {
  return `Scheduler β ${algorithmName} · ${now.format('YYYY-MM-DD HH:mm:ss')}`;
}

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

function recommendedRange(p: SystemParameterView | undefined): ContinuousRange {
  const [lower, upper] = p?.recommended_search_bounds ?? [];
  return { lower: lower ?? null, upper: upper ?? null };
}

export function CreateSystemOptimizationModal({ open, algorithms, objectives, parameters, protocols, onClose }: Props) {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const mutation = useCreateSystemOptimization();
  const scenarios = useSystemScenarios();
  const backends = useSystemBackends();

  const [algorithmId, setAlgorithmId] = useState(
    algorithms.find((a) => a.id === GRID_SEARCH_ID)?.id ?? algorithms[0]?.id ?? '',
  );
  const algorithm = algorithms.find((a) => a.id === algorithmId);
  const detail = useAlgorithm(algorithmId);
  const schema = useMemo(() => detail.data?.metadata.hyperparameter_schema ?? [], [detail.data]);

  const [nameEdited, setNameEdited] = useState(false);
  const [name, setName] = useState(systemOptimizationName(algorithm?.name_en));
  const [scenarioId, setScenarioId] = useState('');
  const [objectiveId, setObjectiveId] = useState(objectives[0]?.id ?? '');
  const [parameterId, setParameterId] = useState(parameters[0]?.definition.id ?? '');
  const [protocolId, setProtocolId] = useState(protocols[0]?.protocol_id ?? '');
  const parameter = parameters.find((p) => p.definition.id === parameterId);
  const [candidateText, setCandidateText] = useState((parameter?.recommended_values ?? []).join(', '));
  const [range, setRange] = useState<ContinuousRange>(recommendedRange(parameter));
  const [mode, setMode] = useState<SettingsMode>('recommended');
  const [hyperparameters, setHyperparameters] = useState<Record<string, HyperparameterValue>>({});
  const [budget, setBudget] = useState<number | null>(null);
  const [requestError, setRequestError] = useState<{ code: string; message: string } | null>(null);

  useEffect(() => setHyperparameters(defaultHyperparameters(schema)), [schema]);

  const selectedScenarioId = scenarioId || scenarios.data?.[0]?.scenario_id || '';
  const scenarioDetail = useSystemScenario(open && selectedScenarioId ? selectedScenarioId : null);
  const scenarioSummary = scenarios.data?.find((s) => s.scenario_id === selectedScenarioId);
  const backend = backends.data?.find((b) => b.id === scenarioSummary?.backend);
  const objective = objectives.find((o) => o.id === objectiveId);
  const protocol = protocols.find((p) => p.protocol_id === protocolId);
  const baselineBeta = scenarioDetail.data?.scenario.simulation.scheduler.beta;

  const kind = algorithm ? editableParameterType(algorithm.supported_parameter_types) : null;
  const validation = useMemo(
    () => (parameter && kind === 'discrete' ? validateCandidates(candidateText, parameter.definition) : null),
    [parameter, kind, candidateText],
  );
  const candidateError =
    validation && 'error' in validation
      ? validation.error
      : validation && validation.values.length > MAX_SYSTEM_CANDIDATES
        ? `最多 ${MAX_SYSTEM_CANDIDATES} 个候选 / At most ${MAX_SYSTEM_CANDIDATES} candidates`
        : null;
  const rangeError = parameter && kind === 'continuous'
    ? continuousRangeError(range, parameter.recommended_search_bounds) : null;

  const spec: ParameterSpec | null = useMemo(() => {
    if (!parameter) return null;
    if (kind === 'discrete') {
      return validation && 'values' in validation
        ? { id: parameter.definition.id, type: 'discrete', choices: validation.values } : null;
    }
    if (kind === 'continuous') {
      return range.lower !== null && range.upper !== null
        ? { id: parameter.definition.id, type: 'continuous', lower: range.lower, upper: range.upper } : null;
    }
    return { id: parameter.definition.id, type: 'continuous' };
  }, [parameter, kind, validation, range]);

  const advanced = mode === 'advanced';
  const hpErrors = advanced ? schema.filter((h) => hyperparameterError(h, hyperparameters[h.id])) : [];
  const userHyperparameters = advanced ? hyperparameters : {};
  const defaultBudget = kind === 'discrete' && spec?.choices ? spec.choices.length : DEFAULT_EVALUATION_BUDGET;
  const effectiveBudget = advanced ? budget ?? defaultBudget : null;

  const bodyKey = spec && objective
    ? JSON.stringify({
        problem_type: 'system',
        scenario_id: selectedScenarioId || undefined,
        objective_id: objective.id,
        parameter_space: { parameters: [spec] },
        algorithm_hyperparameters: userHyperparameters,
        ...(effectiveBudget !== null ? { evaluation_budget: { max_evaluations: effectiveBudget } } : {}),
      } satisfies AlgorithmValidateRequest)
    : null;
  const debouncedKey = useDebounced(bodyKey, VALIDATE_DEBOUNCE_MS);
  const debouncedBody = useMemo(
    () => (debouncedKey ? (JSON.parse(debouncedKey) as AlgorithmValidateRequest) : null),
    [debouncedKey],
  );
  const compat = useAlgorithmValidation(open && algorithm ? algorithm.id : null, debouncedBody);
  const compatible = !!compat.data?.compatible && compat.data.algorithm_id === algorithm?.id && !compat.isError
    && !compat.isFetching && debouncedKey === bodyKey;

  const backendReady = !!backend?.available && backend.capabilities.includes('channel_reuse');
  const canRun =
    !!spec && !candidateError && !rangeError && hpErrors.length === 0 && !!algorithm && !!objective && !!protocol
    && !!selectedScenarioId && backendReady && name.trim().length > 0 && compatible;

  const selectAlgorithm = (id: string) => {
    setAlgorithmId(id);
    setMode('recommended');
    setBudget(null);
    const next = algorithms.find((a) => a.id === id);
    if (!nameEdited) setName(systemOptimizationName(next?.name_en));
  };

  const close = () => {
    if (mutation.isPending) return;
    setRequestError(null);
    mutation.reset();
    onClose();
  };

  const run = async () => {
    if (!canRun || !spec || !algorithm || !objective || !protocol) return;
    setRequestError(null);
    try {
      const opt = await mutation.mutateAsync({
        problem_type: 'system',
        name: name.trim(),
        scenario_id: selectedScenarioId,
        algorithm_id: algorithm.id,
        objective_id: objective.id,
        parameter_space: { parameters: [spec] },
        algorithm_hyperparameters: userHyperparameters,
        ...(effectiveBudget !== null ? { evaluation_budget: { max_evaluations: effectiveBudget } } : {}),
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
      width={760}
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
            <Input value={name} maxLength={120} aria-label="Optimization name"
              onChange={(e) => { setNameEdited(true); setName(e.target.value); }} />
          </Form.Item>
          <Form.Item label="算法 Algorithm（来自 Algorithm Registry）"
            help={algorithm ? <span className="muted">{algorithm.notice_zh}</span> : undefined}>
            <Select
              style={{ width: '100%' }}
              aria-label="Algorithm"
              value={algorithmId || undefined}
              onChange={selectAlgorithm}
              options={algorithms.map((a) => ({ value: a.id, label: `${a.name_zh} · ${a.name_en} (v${a.version})` }))}
            />
          </Form.Item>
          {algorithm && (
            <div className="section-bottom">
              <AlgorithmTags category={algorithm.category} status={algorithm.status} learning={algorithm.learning_algorithm}
                deliverable={algorithm.project_research_deliverable} />
            </div>
          )}
          <Form.Item label="场景 Scenario">
            <Select
              style={{ width: '100%' }}
              aria-label="Scenario"
              value={selectedScenarioId || undefined}
              loading={scenarios.isLoading}
              onChange={setScenarioId}
              options={(scenarios.data ?? []).map((s) => ({ value: s.scenario_id, label: `${s.name_zh} · ${s.scenario_id}` }))}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="优化目标 Objective">
                <Select style={{ width: '100%' }} aria-label="Objective" value={objectiveId || undefined}
                  onChange={setObjectiveId}
                  options={objectives.map((o) => ({ value: o.id, label: `${o.id} (${o.direction})` }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="优化变量 Variable">
                <Select
                  style={{ width: '100%' }}
                  aria-label="Variable"
                  value={parameterId || undefined}
                  onChange={(id: string) => {
                    setParameterId(id);
                    const next = parameters.find((p) => p.definition.id === id);
                    setCandidateText((next?.recommended_values ?? []).join(', '));
                    setRange(recommendedRange(next));
                  }}
                  options={parameters.map((p) => ({ value: p.definition.id, label: `${p.definition.name_en} (${p.definition.id})` }))}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="评估协议 Benchmark Protocol">
                <Select style={{ width: '100%' }} aria-label="Benchmark protocol" value={protocolId || undefined}
                  onChange={setProtocolId}
                  options={protocols.map((p) => ({ value: p.protocol_id, label: `${p.protocol_id} v${p.version}` }))} />
              </Form.Item>
            </Col>
          </Row>
          {parameter && (
            <ParameterSpaceEditor
              kind={kind}
              parameter={parameter}
              baseline={baselineBeta}
              range={range}
              onRange={setRange}
              rangeError={rangeError}
              candidateText={candidateText}
              onCandidateText={setCandidateText}
              candidateError={candidateError}
            />
          )}
          <Collapse
            size="small"
            defaultActiveKey={['settings']}
            items={[
              {
                key: 'settings',
                label: '算法设置 Algorithm Settings',
                children: (
                  <AlgorithmSettings
                    schema={schema}
                    mode={mode}
                    onMode={setMode}
                    values={hyperparameters}
                    onValue={(id, v) => setHyperparameters((h) => ({ ...h, [id]: v }))}
                    budget={budget ?? defaultBudget}
                    defaultBudget={defaultBudget}
                    onBudget={setBudget}
                  />
                ),
              },
              {
                key: 'advanced',
                label: '运行环境 Run Environment',
                children: (
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
                  </Descriptions>
                ),
              },
            ]}
          />
          <CompatibilityFeedback report={compat.data} error={compat.error} checking={compat.isFetching} />
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
