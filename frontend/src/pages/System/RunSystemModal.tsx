import { LoadingOutlined } from '@ant-design/icons';
import { Alert, App, Button, Descriptions, Modal, Result, Space, Spin } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { toApiError } from '../../api/client';
import { useCreateSystemExperiment } from '../../api/system';
import { SystemModelBadge } from '../../components/SystemModelBadge';
import type { SystemBackendView, SystemExperimentResponse, SystemScenarioSummary } from '../../types/system';
import { formatHz } from '../../utils/format';

type Outcome =
  | { kind: 'failed'; experiment: SystemExperimentResponse }
  | { kind: 'request_error'; code: string; message: string };

interface Props {
  open: boolean;
  scenario: SystemScenarioSummary;
  backend: SystemBackendView | undefined;
  onClose: () => void;
}

export function systemExperimentName(scenario: SystemScenarioSummary, now = dayjs()): string {
  return `${scenario.name_en} · ${now.format('YYYY-MM-DD HH:mm:ss')}`.slice(0, 200);
}

export function RunSystemModal({ open, scenario, backend, onClose }: Props) {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const mutation = useCreateSystemExperiment();
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const running = mutation.isPending;

  const close = () => {
    if (running) return;
    setOutcome(null);
    mutation.reset();
    onClose();
  };

  const run = async () => {
    setOutcome(null);
    try {
      const exp = await mutation.mutateAsync({
        name: systemExperimentName(scenario),
        scenario_id: scenario.scenario_id,
        backend_id: backend?.id,
      });
      if (exp.status === 'failed') {
        setOutcome({ kind: 'failed', experiment: exp });
        return;
      }
      if (exp.status === 'succeeded') message.success('系统级仿真完成 / System simulation succeeded');
      onClose();
      navigate(`/system/experiments/${exp.experiment_id}`);
    } catch (err) {
      const apiError = toApiError(err);
      setOutcome({ kind: 'request_error', code: apiError.code, message: `${apiError.messageZh} / ${apiError.messageEn}` });
    }
  };

  const failed = outcome?.kind === 'failed' ? outcome.experiment : null;

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
      <Button key="detail" type="primary" onClick={() => { close(); navigate(`/system/experiments/${failed.experiment_id}`); }}>
        查看实验详情 View Experiment
      </Button>,
    ];
  } else {
    footer = [
      <Button key="cancel" onClick={close}>取消</Button>,
      <Button key="run" type="primary" onClick={run} disabled={!backend?.available}>
        {outcome ? '重新运行' : '开始运行'}
      </Button>,
    ];
  }

  return (
    <Modal
      open={open}
      title={<span>运行系统级仿真 <span className="card-title-en">Run System Simulation</span></span>}
      onCancel={close}
      closable={!running}
      mask={{ closable: !running }}
      keyboard={!running}
      footer={footer}
      width={600}
    >
      {running ? (
        <div className="run-progress" data-testid="system-running">
          <Spin indicator={<LoadingOutlined spin />} size="large" />
          <div className="run-progress__title">正在执行系统级仿真</div>
          <div className="muted">传播 → PHY → 调度 → UE 吞吐率 → KPI。请勿关闭页面。</div>
          <div className="muted">Propagation → PHY → Scheduling → UE throughput → KPI</div>
        </div>
      ) : outcome ? (
        <Result
          status="error"
          className="run-result"
          title="系统级仿真失败 System Simulation Failed"
          subTitle={
            outcome.kind === 'failed' ? (
              <Space orientation="vertical" size={2}>
                <span>实验编号 <code>{outcome.experiment.experiment_id}</code></span>
                {outcome.experiment.error ? (
                  <>
                    <code>{outcome.experiment.error.code}</code>
                    <span>{outcome.experiment.error.message}</span>
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
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="场景 Scenario">
              {scenario.name_zh}
              <div className="muted">{scenario.scenario_id}</div>
            </Descriptions.Item>
            <Descriptions.Item label="规模 Scale">
              {scenario.bs_count} BS · {scenario.cell_count} Cell · {scenario.ue_count} UE · 下行 Downlink
            </Descriptions.Item>
            <Descriptions.Item label="载频 / 带宽">
              {formatHz(scenario.carrier_frequency_hz)} / {formatHz(scenario.bandwidth_hz)}
            </Descriptions.Item>
            <Descriptions.Item label="后端 Backend">
              {backend ? `${backend.name_zh}${backend.version ? ` v${backend.version}` : ''}` : scenario.backend}
            </Descriptions.Item>
            <Descriptions.Item label="结果来源 Result Source">
              <SystemModelBadge modelType={backend?.model_type} />
            </Descriptions.Item>
            <Descriptions.Item label="随机种子 Seed">{scenario.seed}</Descriptions.Item>
          </Descriptions>
          {backend?.compute_device === 'cpu' && (
            <Alert
              className="section"
              type="info"
              showIcon
              title="系统级计算在 CPU 上运行，预计约 1 分钟。System-level computation runs on CPU (~1 min)."
            />
          )}
          {!backend?.available && (
            <Alert
              className="section"
              type="error"
              showIcon
              title="系统级仿真后端当前不可用。System backend unavailable."
              description={backend?.reason ?? undefined}
            />
          )}
        </>
      )}
    </Modal>
  );
}
