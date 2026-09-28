import { Card, Statistic, Typography } from 'antd';

import type { LayerStatistics } from '../../types/experiment';
import { formatPercent, formatValue, isNumber } from '../../utils/format';
import { metricLabel } from '../../utils/status';

interface Props {
  stats: LayerStatistics;
  primary?: boolean;
}

export function MetricCard({ stats, primary = false }: Props) {
  const label = metricLabel(stats.metric);
  const unit = stats.unit ?? undefined;
  return (
    <Card size="small" className={primary ? 'metric-card metric-card--primary' : 'metric-card'}>
      <div className="metric-card__label">
        <span className="metric-card__label-en">{label.en}</span>
        <span className="metric-card__label-zh">{label.zh}</span>
      </div>
      <Statistic
        title="均值 Mean"
        value={isNumber(stats.mean) ? stats.mean : '—'}
        precision={1}
        suffix={isNumber(stats.mean) ? unit : undefined}
      />
      <Typography.Text type="secondary" className="metric-card__range">
        范围 Range：{formatValue(stats.min, null)} ~ {formatValue(stats.max, unit)}
      </Typography.Text>
      <Typography.Text type="secondary" className="metric-card__range">
        有效格点 Covered cells：{stats.num_covered_cells} / {stats.num_cells}（{formatPercent(stats.coverage_ratio)}）
      </Typography.Text>
    </Card>
  );
}
