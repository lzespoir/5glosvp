import { Tag } from 'antd';

import type { AlgorithmCategory, AlgorithmStatus } from '../../types/algorithm';
import { categoryMeta, statusMeta } from '../../utils/algorithm';

interface Props {
  category: AlgorithmCategory;
  status?: AlgorithmStatus;
  learning: boolean;
  deliverable?: boolean;
}

/** 分类 / 状态 / 学习标记；learning=false 时明确标注，避免被误读为学习优化算法。 */
export function AlgorithmTags({ category, status, learning, deliverable }: Props) {
  const c = categoryMeta(category);
  const s = status ? statusMeta(status) : null;
  return (
    <span data-testid="algorithm-tags">
      <Tag color={c.color}>{c.zh} {c.en}</Tag>
      {s && <Tag color={s.color}>{s.en}</Tag>}
      <Tag color={learning ? 'blue' : 'default'}>{learning ? 'Learning Algorithm' : 'Not Learning Algorithm'}</Tag>
      {deliverable === false && <Tag>Not Project Research Deliverable</Tag>}
    </span>
  );
}
