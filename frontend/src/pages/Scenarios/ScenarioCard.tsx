import { PlayCircleOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Collapse, Descriptions, Skeleton, Tooltip } from 'antd';
import { useState } from 'react';

import { useScenario } from '../../api/scenarios';
import { ErrorState } from '../../components/ErrorState';
import { ProvenanceTag } from '../../components/ProvenanceTag';
import type { BackendInfo } from '../../types/backend';
import type { ScenarioDetail, ScenarioSummary } from '../../types/scenario';
import { EMPTY, formatHz, formatValue, formatVector } from '../../utils/format';
import { RunExperimentModal } from './RunExperimentModal';

interface Props {
  scenario: ScenarioSummary;
  backend: BackendInfo | undefined;
  backendsLoaded: boolean;
}

function ParameterDetails({ detail }: { detail: ScenarioDetail }) {
  const tx = detail.transmitters[0];
  return (
    <Descriptions column={{ xs: 1, md: 2 }} size="small">
      <Descriptions.Item label="发射机数量 Transmitters">{detail.transmitters.length}</Descriptions.Item>
      <Descriptions.Item label="发射机 ID TX">{detail.transmitters.map((t) => t.id).join(', ') || EMPTY}</Descriptions.Item>
      <Descriptions.Item label="发射机位置 TX Position (m)">{formatVector(tx?.position)}</Descriptions.Item>
      <Descriptions.Item label="发射功率 TX Power">{formatValue(tx?.power_dbm, 'dBm')}</Descriptions.Item>
      <Descriptions.Item label="栅格尺寸 Cell Size (m)">{formatVector(detail.radio_map?.cell_size)}</Descriptions.Item>
      <Descriptions.Item label="指标 Metric">{detail.radio_map?.metric?.toUpperCase() ?? EMPTY}</Descriptions.Item>
      <Descriptions.Item label="最大反射深度 Max Depth">{detail.radio_map?.max_depth ?? EMPTY}</Descriptions.Item>
      <Descriptions.Item label="随机种子 Seed">{detail.random_seed ?? EMPTY}</Descriptions.Item>
    </Descriptions>
  );
}

export function ScenarioCard({ scenario, backend, backendsLoaded }: Props) {
  const [open, setOpen] = useState(false);
  const detail = useScenario(scenario.scenario_id);
  const available = backend?.available === true;

  let disabledReason: string | null = null;
  if (!backendsLoaded) disabledReason = '正在检查后端状态 / Checking backend';
  else if (!backend) disabledReason = `后端 ${scenario.backend} 未注册 / Backend not registered`;
  else if (!available) disabledReason = '仿真后端当前不可用 / Simulation backend unavailable';

  return (
    <Card
      className="scenario-card"
      title={
        <div>
          <div className="scenario-card__name">{scenario.name_zh}</div>
          <div className="card-title-en">{scenario.name_en}</div>
        </div>
      }
      extra={backend ? <ProvenanceTag sourceType={backend.source_type} /> : null}
    >
      {detail.isLoading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : detail.isError ? (
        <ErrorState compact error={detail.error} onRetry={() => detail.refetch()} />
      ) : (
        <Descriptions column={{ xs: 1, md: 2 }} size="small">
          <Descriptions.Item label="场景编号 Scenario ID"><code>{scenario.scenario_id}</code></Descriptions.Item>
          <Descriptions.Item label="仿真后端 Backend">
            {backend ? `${backend.name_zh}${backend.version ? ` v${backend.version}` : ''}` : scenario.backend}
          </Descriptions.Item>
          <Descriptions.Item label="场景 Scene">{detail.data?.scene_name ?? EMPTY}</Descriptions.Item>
          <Descriptions.Item label="载波频率 Frequency">{formatHz(detail.data?.frequency_hz)}</Descriptions.Item>
          <Descriptions.Item label="带宽 Bandwidth">{formatHz(detail.data?.bandwidth_hz)}</Descriptions.Item>
          <Descriptions.Item label="随机种子 Seed">{detail.data?.random_seed ?? EMPTY}</Descriptions.Item>
          <Descriptions.Item label="数据类型 Data Type">
            {backend ? <ProvenanceTag sourceType={backend.source_type} /> : EMPTY}
          </Descriptions.Item>
        </Descriptions>
      )}

      {detail.data && (
        <Collapse
          ghost
          size="small"
          className="scenario-card__params"
          items={[{ key: 'params', label: '场景参数 Parameters', children: <ParameterDetails detail={detail.data} /> }]}
        />
      )}

      {backendsLoaded && backend && !available && (
        <Alert
          type="error"
          showIcon
          className="section"
          title="仿真后端当前不可用，无法运行实验。"
          description={backend.reason ?? 'Simulation backend unavailable.'}
        />
      )}

      <div className="scenario-card__actions">
        <Tooltip title={disabledReason}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            disabled={disabledReason !== null}
            onClick={() => setOpen(true)}
          >
            运行实验 Run Experiment
          </Button>
        </Tooltip>
      </div>

      <RunExperimentModal open={open} scenario={scenario} backend={backend} onClose={() => setOpen(false)} />
    </Card>
  );
}
