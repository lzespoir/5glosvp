import { Descriptions, Tag } from 'antd';

import type { SystemOptimizationResponse } from '../../types/systemOptimization';

interface Props {
  optimization: SystemOptimizationResponse;
}

const FIELDS: [string, string][] = [
  ['optimizer', '优化器 Optimizer'],
  ['optimizer_version', '优化器版本 Optimizer Version'],
  ['optimizer_category', '类别 Category'],
  ['objective', '目标 Objective'],
  ['objective_version', '目标版本 Objective Version'],
  ['benchmark_protocol', '协议 Protocol'],
  ['backend', '后端 Backend'],
  ['backend_version', '后端版本 Backend Version'],
  ['model_label', '模型 Model'],
  ['source_type', '数据类型 Source Type'],
  ['evidence_level', '证据等级 Evidence Level'],
  ['search_space_source', '搜索空间来源 Search Space Source'],
  ['parameter_source', '参数来源 Parameter Source'],
  ['seed', '随机种子 Seed'],
  ['git_commit', 'Git Commit'],
];

const FLAGS: [string, string][] = [
  ['learning_algorithm', 'Learning Algorithm'],
  ['measured', 'Measured'],
  ['huawei_data', 'Huawei Data'],
  ['acceptance_evidence', 'Acceptance Evidence'],
];

export function SystemOptimizationProvenance({ optimization: o }: Props) {
  const p = o.provenance;
  return (
    <Descriptions column={1} size="small" data-testid="system-optimization-provenance">
      {FIELDS.filter(([k]) => p[k] !== undefined && p[k] !== null).map(([k, label]) => (
        <Descriptions.Item key={k} label={label}>
          {k === 'git_commit' ? <code>{String(p[k]).slice(0, 12)}</code> : String(p[k])}
        </Descriptions.Item>
      ))}
      {FLAGS.map(([k, label]) => (
        <Descriptions.Item key={k} label={label}>
          <Tag>{p[k] === true ? 'Yes' : 'No'}</Tag>
        </Descriptions.Item>
      ))}
    </Descriptions>
  );
}
