import { Card, Typography } from 'antd';

interface Props {
  titleZh: string;
  titleEn: string;
  reasonZh: string;
  reasonEn: string;
}

/** 尚未实现的 KPI：固定显示 “—”，不填充任何数值。 */
export function EmptyMetric({ titleZh, titleEn, reasonZh, reasonEn }: Props) {
  return (
    <Card size="small" className="metric-card metric-card--empty">
      <div className="metric-card__label">
        <span className="metric-card__label-en">{titleEn}</span>
        <span className="metric-card__label-zh">{titleZh}</span>
      </div>
      <div className="metric-card__empty-value">—</div>
      <Typography.Text type="secondary" className="metric-card__range">
        {reasonZh}
      </Typography.Text>
      <Typography.Text type="secondary" className="metric-card__range">
        {reasonEn}
      </Typography.Text>
    </Card>
  );
}
