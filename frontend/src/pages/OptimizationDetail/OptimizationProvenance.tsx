import { Descriptions, Tag } from 'antd';

import { ProvenanceTag } from '../../components/ProvenanceTag';
import type { SourceType } from '../../types/common';
import type { OptimizationResponse } from '../../types/optimization';
import { EMPTY } from '../../utils/format';

function text(v: unknown): string {
  return typeof v === 'string' || typeof v === 'number' ? String(v) : EMPTY;
}

function isSourceType(v: unknown): v is SourceType {
  return v === 'simulation' || v === 'test_fixture';
}

export function OptimizationProvenance({ optimization }: { optimization: OptimizationResponse }) {
  const p = optimization.provenance;
  return (
    <Descriptions column={1} size="small">
      <Descriptions.Item label="优化器 Optimizer">
        {optimization.optimizer.name_en ?? text(p.optimizer)}
      </Descriptions.Item>
      <Descriptions.Item label="类别 Category">工程基线 Engineering Baseline</Descriptions.Item>
      <Descriptions.Item label="Learning Algorithm">
        <Tag>{p.learning_algorithm === true ? 'Yes' : 'No'}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="仿真 Simulation">{text(p.simulation_backend)}</Descriptions.Item>
      <Descriptions.Item label="数据类型 Data Type">
        <ProvenanceTag sourceType={isSourceType(p.source_type) ? p.source_type : undefined} />
      </Descriptions.Item>
      <Descriptions.Item label="实测数据 Measured">{p.measured === true ? 'Yes' : 'No'}</Descriptions.Item>
      <Descriptions.Item label="目标函数 Objective">
        {text(p.objective_id)} <span className="muted">v{text(p.objective_version)}</span>
      </Descriptions.Item>
      <Descriptions.Item label="随机种子 Seed">{optimization.seed}（所有候选相同 Same for all）</Descriptions.Item>
      <Descriptions.Item label="证据等级 Evidence">{text(p.evidence_level)}</Descriptions.Item>
      <Descriptions.Item label="搜索空间 Space">{text(p.search_space_source)}</Descriptions.Item>
    </Descriptions>
  );
}
