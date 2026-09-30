import { Alert, Card } from 'antd';
import { PageHeader } from '../../components/PageHeader';
import { AntennaPatternViewer } from './AntennaPatternViewer';

export function AntennaWorkspacePage() {
  return <>
    <PageHeader titleZh="天线与配置资产" titleEn="Antenna Pattern Workspace" subtitle="A-Matrix 是天线方向图 Provider；选择 profile/beam、检查球面相对响应与数据 provenance。" />
    <Alert className="section-bottom" type="warning" showIcon message="相对响应，不是绝对增益" description="默认 3D 球面半径表示各波束 peak-normalized relative response；不代表 dBi、dBm 或实测 RSRP/SINR。多波束仅作视觉叠加。" />
    <Card>
      <AntennaPatternViewer />
    </Card>
  </>;
}
