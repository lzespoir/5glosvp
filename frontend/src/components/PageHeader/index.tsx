import { Typography } from 'antd';
import type { ReactNode } from 'react';

interface Props {
  titleZh: string;
  titleEn: string;
  subtitle?: ReactNode;
  extra?: ReactNode;
}

export function PageHeader({ titleZh, titleEn, subtitle, extra }: Props) {
  return (
    <div className="page-header">
      <div>
        <Typography.Title level={3} className="page-header__title">
          {titleZh}
          <span className="page-header__title-en">{titleEn}</span>
        </Typography.Title>
        {subtitle && <div className="page-header__subtitle">{subtitle}</div>}
      </div>
      {extra && <div className="page-header__extra">{extra}</div>}
    </div>
  );
}
