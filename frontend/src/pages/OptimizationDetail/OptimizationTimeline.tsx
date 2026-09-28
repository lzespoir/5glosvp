import { Empty, Timeline } from 'antd';

import type { OptimizationEvent } from '../../types/optimization';
import { formatDateTime } from '../../utils/format';
import { eventLabel } from '../../utils/optimization';

function eventColor(event: string): string {
  if (event.endsWith('_failed')) return 'red';
  if (event === 'optimization_completed' || event === 'best_candidate_selected') return 'green';
  return 'blue';
}

/** 优化时间线：只使用后端记录的 events 及其真实时间戳。 */
export function OptimizationTimeline({ events }: { events: OptimizationEvent[] }) {
  if (events.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无事件 / No events" />;
  }
  return (
    <Timeline
      items={events.map((e, i) => {
        const label = eventLabel(e.event);
        return {
          key: `${e.event}-${i}`,
          color: eventColor(e.event),
          content: (
            <div>
              <strong>{label.zh}</strong> <span className="muted">{label.en}</span>
              {e.candidate_id && <> · <code>{e.candidate_id}</code></>}
              <div className="muted timeline-time">{formatDateTime(e.at)}</div>
            </div>
          ),
        };
      })}
    />
  );
}
