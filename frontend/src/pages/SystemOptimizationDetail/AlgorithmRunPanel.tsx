import { Descriptions, Tag, Tooltip } from 'antd';
import { Link } from 'react-router-dom';

import type { SystemOptimizationResponse } from '../../types/systemOptimization';
import { algorithmPath, formatHyperparameter, shortHash, stopReasonMeta } from '../../utils/algorithm';
import { formatParameter } from '../../utils/systemOptimization';
import { AlgorithmTags } from '../Algorithms/AlgorithmTags';

/** 算法身份、超参数、预算、停止原因与 provenance（全部来自后端记录）。 */
export function AlgorithmRunPanel({ optimization: o }: { optimization: SystemOptimizationResponse }) {
  const info = o.algorithm;
  const budget = o.evaluation_budget;
  const trace = o.algorithm_trace;
  if (!info) {
    return (
      <Descriptions column={1} size="small" data-testid="algorithm-run-panel">
        <Descriptions.Item label="算法 Algorithm"><code>{o.optimizer_id}</code> v{o.optimizer_version}</Descriptions.Item>
        <Descriptions.Item label="说明 Note">Day 6 记录（算法接入框架之前），无算法 trace。Recorded before Day 7.</Descriptions.Item>
      </Descriptions>
    );
  }
  const stop = o.stop_reason ? stopReasonMeta(o.stop_reason) : null;
  const pid = o.parameter.id;
  const recommended = trace?.recommendation?.parameters?.[pid];
  const hps = Object.entries(info.hyperparameters);
  return (
    <Descriptions column={1} size="small" data-testid="algorithm-run-panel">
      <Descriptions.Item label="算法 Algorithm">
        <Link to={algorithmPath(info.algorithm_id)}>{info.algorithm_name_zh}</Link>{' '}
        <span className="muted">{info.algorithm_name_en} · <code>{info.algorithm_id}</code></span>
      </Descriptions.Item>
      <Descriptions.Item label="版本 Version">v{info.algorithm_version} · SDK {info.sdk_version}</Descriptions.Item>
      <Descriptions.Item label="分类 Category">
        <AlgorithmTags category={info.algorithm_category} learning={info.learning_algorithm}
          deliverable={info.project_research_deliverable} />
      </Descriptions.Item>
      <Descriptions.Item label="超参数 Hyperparameters">
        {hps.length ? hps.map(([k, v]) => <Tag key={k}>{k} = {formatHyperparameter(v)}</Tag>) : '无 None'}
        <Tag color={info.auto_configured ? 'green' : 'blue'}>{info.auto_configured ? 'Recommended' : 'Advanced'}</Tag>
      </Descriptions.Item>
      {budget && (
        <Descriptions.Item label="评价预算 Budget">
          <span data-testid="evaluation-budget">
            已用 Used {budget.evaluations_used} / {budget.max_evaluations} · 仿真 Simulations {budget.simulations_run} ·
            缓存命中 Cache hits {budget.cache_hits}
            {budget.rejected_suggestions > 0 && <> · 拒绝建议 Rejected {budget.rejected_suggestions}</>}
          </span>
        </Descriptions.Item>
      )}
      <Descriptions.Item label="停止原因 Stop Reason">
        {stop ? (
          <span data-testid="stop-reason">
            <Tag color={stop.color}>{stop.en}</Tag>{stop.zh}
            {trace?.stop_detail && <span className="muted"> · {trace.stop_detail}</span>}
          </span>
        ) : '—'}
      </Descriptions.Item>
      <Descriptions.Item label="算法推荐 Recommendation">
        {recommended !== undefined ? (
          <>
            {pid} = {formatParameter(recommended)}{' '}
            {o.recommendation_matches_best !== null && o.recommendation_matches_best !== undefined && (
              <Tag>{o.recommendation_matches_best ? '与平台最优一致 Matches best' : '与平台最优不同 Differs from best'}</Tag>
            )}
          </>
        ) : (
          <span className="muted">由平台按统一规则选择最优 Platform selects best</span>
        )}
      </Descriptions.Item>
      <Descriptions.Item label="配置哈希 Config Hash">
        <Tooltip title={info.algorithm_config_hash}><code>{shortHash(info.algorithm_config_hash)}</code></Tooltip>
      </Descriptions.Item>
      <Descriptions.Item label="参数空间哈希 Space Hash">
        <Tooltip title={info.parameter_space_hash}><code>{shortHash(info.parameter_space_hash)}</code></Tooltip>
      </Descriptions.Item>
      <Descriptions.Item label="源码 Source">
        <code>{info.source}</code>{' '}
        <span className="muted">@ {shortHash(info.source_revision.value ?? null, 10)}</span>
      </Descriptions.Item>
    </Descriptions>
  );
}
