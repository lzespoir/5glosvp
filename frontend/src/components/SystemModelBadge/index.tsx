import { Tag, Tooltip } from 'antd';

import type { SystemModelType } from '../../types/system';
import { modelMeta } from '../../utils/system';

interface Props {
  modelType: SystemModelType | null | undefined;
}

/** 结果来源徽标：Sionna 仿真 / 快速工程近似 / 测试夹具视觉上明确区分。 */
export function SystemModelBadge({ modelType }: Props) {
  const meta = modelMeta(modelType);
  return (
    <Tooltip title={meta.labelZh}>
      <Tag color={meta.color} className={`model-badge ${meta.className}`} data-testid="model-badge">
        {meta.label}
      </Tag>
    </Tooltip>
  );
}
