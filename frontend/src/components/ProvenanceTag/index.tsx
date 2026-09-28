import { ExperimentOutlined, ToolOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

import { dataTypeMeta } from '../../utils/status';

interface Props {
  sourceType: string | null | undefined;
}

export function ProvenanceTag({ sourceType }: Props) {
  const meta = dataTypeMeta(sourceType);
  const icon = meta.kind === 'test_fixture' ? <ToolOutlined /> : <ExperimentOutlined />;
  return (
    <Tag color={meta.color} icon={icon} className="provenance-tag">
      {meta.zh} / {meta.en}
    </Tag>
  );
}
