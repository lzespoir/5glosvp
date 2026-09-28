import { Empty, Timeline } from 'antd';

import type { StatusTransitionView } from '../../types/experiment';
import { formatDateTime } from '../../utils/format';
import { statusMeta } from '../../utils/status';

const TIMELINE_COLORS = { default: 'gray', processing: 'blue', success: 'green', error: 'red' } as const;

/** 实验时间线：只使用 API 返回的 status_history 及其真实时间戳。 */
export function StatusTimeline({ history }: { history: StatusTransitionView[] }) {
  if (history.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无状态记录 / No status history" />;
  }
  return (
    <Timeline
      items={history.map((h, i) => {
        const meta = statusMeta(h.status);
        return {
          key: `${h.status}-${i}`,
          color: TIMELINE_COLORS[meta.color],
          content: (
            <div>
              <strong>{meta.zh}</strong> <span className="muted">{meta.en}</span>
              <div className="muted timeline-time">{formatDateTime(h.at)}</div>
            </div>
          ),
        };
      })}
    />
  );
}
