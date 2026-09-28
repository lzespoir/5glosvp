import { Card, Descriptions, Tag, Typography } from 'antd';

import type { ImprovementStatus, OptimizationComparison } from '../../types/optimization';
import {
  formatObjective,
  formatPower,
  formatSigned,
  improvementMeta,
  type ImprovementMeta,
  TX_POWER,
} from '../../utils/optimization';

const TEXT_TYPE: Record<ImprovementMeta['color'], 'success' | 'secondary' | 'warning'> = {
  success: 'success',
  default: 'secondary',
  warning: 'warning',
};

interface Props {
  comparison: OptimizationComparison;
  status: ImprovementStatus;
}

/** 目标函数改善与参数对比：数值全部来自后端 comparison，前端不计算。 */
export function ObjectiveComparison({ comparison, status }: Props) {
  const meta = improvementMeta(status);
  const textType = TEXT_TYPE[meta.color];
  return (
    <Card
      size="small"
      title={<span>优化目标改善 <span className="card-title-en">Objective Improvement</span></span>}
      extra={<Tag color={meta.color} data-testid="improvement-status">{meta.zh} {meta.en}</Tag>}
      className="fill-height"
    >
      <div className="objective-delta">
        <Typography.Text type={textType} className="objective-delta__value" data-testid="absolute-improvement">
          ΔJ {formatSigned(comparison.absolute_improvement)}
        </Typography.Text>
        <Typography.Text type={textType} data-testid="relative-improvement">
          {comparison.relative_improvement_percent === null
            ? '相对改善不可用（基线 ≈ 0）/ Relative N/A'
            : `相对 ${formatSigned(comparison.relative_improvement_percent, 2, '%')}`}
        </Typography.Text>
      </div>
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="基线目标 Baseline J">{formatObjective(comparison.baseline_objective)}</Descriptions.Item>
        <Descriptions.Item label="最优目标 Optimized J">{formatObjective(comparison.optimized_objective)}</Descriptions.Item>
        <Descriptions.Item label="TX Power 参数">
          {formatPower(comparison.baseline_parameters[TX_POWER])} → <strong>{formatPower(comparison.optimized_parameters[TX_POWER])}</strong>
        </Descriptions.Item>
        <Descriptions.Item label="最优候选 Best">
          <code>{comparison.optimized_candidate_id}</code>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
