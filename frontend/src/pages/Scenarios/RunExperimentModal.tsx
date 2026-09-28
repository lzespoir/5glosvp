import { LoadingOutlined } from '@ant-design/icons';
import { Alert, App, Button, Descriptions, Modal, Result, Space, Spin } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { toApiError } from '../../api/client';
import { useCreateExperiment } from '../../api/experiments';
import { ProvenanceTag } from '../../components/ProvenanceTag';
import type { BackendInfo } from '../../types/backend';
import type { ExperimentResponse } from '../../types/experiment';
import type { ScenarioSummary } from '../../types/scenario';
import { isExperimentFailed, isExperimentSucceeded } from '../../utils/status';

type Outcome =
  | { kind: 'failed'; experiment: ExperimentResponse }
  | { kind: 'request_error'; code: string; message: string };

interface Props {
  open: boolean;
  scenario: ScenarioSummary;
  backend: BackendInfo | undefined;
  onClose: () => void;
}

export function experimentName(scenario: ScenarioSummary, now = dayjs()): string {
  return `${scenario.name_en} · ${now.format('YYYY-MM-DD HH:mm:ss')}`.slice(0, 200);
}

export function RunExperimentModal({ open, scenario, backend, onClose }: Props) {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const mutation = useCreateExperiment();
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
      const exp = await mutation.mutateAsync({ name: experimentName(scenario), scenario_id: scenario.scenario_id });
      if (isExperimentSucceeded(exp)) {
        message.success('实验运行成功 / Experiment succeeded');
        onClose();
        navigate(`/experiments/${exp.experiment_id}`);
      } else if (isExperimentFailed(exp)) {
        setOutcome({ kind: 'failed', experiment: exp });
      } else {
        onClose();
        navigate(`/experiments/${exp.experiment_id}`);
      }
    } catch (err) {
      const apiError = toApiError(err);
      setOutcome({ kind: 'request_error', code: apiError.code, message: `${apiError.messageZh} / ${apiError.messageEn}` });
    }
  };

  const failedExperiment = outcome?.kind === 'failed' ? outcome.experiment : null;

  let footer;
  if (running) {
    footer = [
      <Button key="running" type="primary" loading disabled>
        运行中... Running...
      </Button>,
    ];
  } else if (failedExperiment) {
    footer = [
      <Button key="close" onClick={close}>关闭 Close</Button>,
      <Button key="detail" type="primary" onClick={() => { close(); navigate(`/experiments/${failedExperiment.experiment_id}`); }}>
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
      title={<span>运行实验 <span className="card-title-en">Run Experiment</span></span>}
      onCancel={close}
      closable={!running}
      mask={{ closable: !running }}
      keyboard={!running}
      footer={footer}
      width={560}
    >
      {running ? (
        <div className="run-progress">
          <Spin indicator={<LoadingOutlined spin />} size="large" />
          <div className="run-progress__title">正在执行 Sionna RT 仿真</div>
          <div className="muted">Running ray-tracing simulation. 请勿关闭页面。</div>
        </div>
      ) : outcome ? (
        <Result
          status="error"
          className="run-result"
          title="实验执行失败 Experiment Failed"
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
            <Descriptions.Item label="后端 Backend">
              {backend ? `${backend.name_zh}${backend.version ? ` v${backend.version}` : ''}` : scenario.backend}
            </Descriptions.Item>
            <Descriptions.Item label="数据类型 Data Type">
              <ProvenanceTag sourceType={backend?.source_type} />
            </Descriptions.Item>
          </Descriptions>
          {!backend?.available && (
            <Alert
              className="section"
              type="error"
              showIcon
              title="仿真后端当前不可用，无法运行实验。Simulation backend unavailable."
              description={backend?.reason ?? undefined}
            />
          )}
        </>
      )}
    </Modal>
  );
}
