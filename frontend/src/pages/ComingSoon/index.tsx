import { ClockCircleOutlined } from '@ant-design/icons';
import { Result } from 'antd';

import { PageHeader } from '../../components/PageHeader';

interface Props {
  titleZh: string;
  titleEn: string;
}

export function ComingSoon({ titleZh, titleEn }: Props) {
  return (
    <>
      <PageHeader titleZh={titleZh} titleEn={titleEn} />
      <Result
        icon={<ClockCircleOutlined />}
        title="即将开放 / Coming Soon"
        subTitle="该模块尚未开发，当前不展示任何数据。This module is not available yet."
      />
    </>
  );
}
