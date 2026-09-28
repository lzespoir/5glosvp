import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons';
import { Descriptions, Space, Tag, Tooltip, Typography } from 'antd';

import type { SystemOptimizationResponse } from '../../types/systemOptimization';

interface Props {
  optimization: SystemOptimizationResponse;
}

function short(hash: string) {
  return (
    <Tooltip title={hash}>
      <Typography.Text code copyable={{ text: hash }}>{hash.slice(0, 12)}…</Typography.Text>
    </Tooltip>
  );
}

/** 冻结评估协议 + 公共评估上下文 + 后端复核的公平性检查。 */
export function EvaluationProtocolPanel({ optimization: o }: Props) {
  const p = o.benchmark_protocol;
  const ctx = o.evaluation_context;
  return (
    <>
      <div className="section-label">Fair Evaluation Conditions</div>
      <Space wrap className="section-bottom" data-testid="fairness-badges">
        {(o.fairness?.checks ?? []).map((c) => (
          <Tooltip key={c.id} title={c.detail}>
            <Tag
              color={c.passed ? 'success' : 'error'}
              icon={c.passed ? <CheckCircleFilled /> : <CloseCircleFilled />}
              data-testid={`fairness-${c.id}`}
            >
              {c.label_zh} {c.label_en}
            </Tag>
          </Tooltip>
        ))}
        {!o.fairness && <span className="muted">尚未生成公平性报告 / Fairness report not available yet</span>}
      </Space>
      <Descriptions column={{ xs: 1, lg: 2 }} size="small" bordered>
        <Descriptions.Item label="协议 Protocol">
          <Tag color="purple">{p.protocol_id} v{p.version}</Tag> <span className="muted">frozen {p.frozen_at}</span>
        </Descriptions.Item>
        <Descriptions.Item label="时隙 Horizon">
          {p.simulation_slots} slots · warm-up {p.warmup_slots}
        </Descriptions.Item>
        <Descriptions.Item label="重复 Repeats">{p.num_repeats} · {p.aggregation_method}</Descriptions.Item>
        <Descriptions.Item label="种子策略 Seed Policy">{p.seed_policy}</Descriptions.Item>
        <Descriptions.Item label="已观测波动 Observed Variability" span="filled">
          ±{p.observed_variability.relative_percent}% ({p.observed_variability.kpi_id})
          <div className="muted">{p.observed_variability.description_zh}</div>
        </Descriptions.Item>
        {ctx && (
          <>
            <Descriptions.Item label="评估上下文 Context"><code>{ctx.context_id}</code></Descriptions.Item>
            <Descriptions.Item label="场景版本 Scenario Version">{short(ctx.scenario_version)}</Descriptions.Item>
            <Descriptions.Item label="信道实现 Channel">
              <code>{ctx.channel_realization.channel_realization_id}</code> {short(ctx.channel_realization.sha256)}
            </Descriptions.Item>
            <Descriptions.Item label="UE 集合 UE Population">
              <code>{ctx.ue_population.ue_population_id}</code> ({ctx.ue_population.ues.length} UEs){' '}
              {short(ctx.ue_population.sha256)}
            </Descriptions.Item>
            <Descriptions.Item label="业务 Traffic">
              <code>{ctx.traffic_realization.traffic_realization_id}</code> {short(ctx.traffic_realization.sha256)}
            </Descriptions.Item>
            <Descriptions.Item label="后端 Backend">
              {ctx.backend_id} {ctx.backend_version && <Tag>v{ctx.backend_version}</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="哈希规则 Hash Rule" span="filled">
              <span className="muted">{ctx.channel_realization.hash_rule}</span>
            </Descriptions.Item>
          </>
        )}
      </Descriptions>
      {p.limitations.length > 0 && (
        <ul className="plain-list section muted">
          {p.limitations.map((l) => <li key={l}>{l}</li>)}
        </ul>
      )}
    </>
  );
}
