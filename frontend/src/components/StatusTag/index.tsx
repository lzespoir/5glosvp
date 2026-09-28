import { Tag, Tooltip } from 'antd';

import type { ExperimentStatus } from '../../types/experiment';
import { statusMeta } from '../../utils/status';

interface Props {
  status: ExperimentStatus;
  /** 同时显示英文副文字 */
  showEn?: boolean;
}

export function StatusTag({ status, showEn = false }: Props) {
  const meta = statusMeta(status);
  return (
    <Tooltip title={meta.en}>
      <Tag color={meta.color} className="status-tag">
        {meta.zh}
        {showEn && <span className="status-tag__en">{meta.en}</span>}
      </Tag>
    </Tooltip>
  );
}
