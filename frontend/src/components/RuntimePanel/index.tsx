import { Descriptions } from 'antd';

import type { RuntimeView } from '../../types/experiment';
import { EMPTY, formatSeconds, isNumber } from '../../utils/format';

interface Props {
  runtime: RuntimeView;
}

const FIELDS: { key: keyof RuntimeView; zh: string; en: string }[] = [
  { key: 'scenario_load_seconds', zh: '场景加载', en: 'Scene Load' },
  { key: 'simulation_seconds', zh: '仿真计算', en: 'Simulation' },
  { key: 'artifact_export_seconds', zh: '产物导出', en: 'Artifact Export' },
  { key: 'total_seconds', zh: '总耗时', en: 'Total' },
];

export function RuntimePanel({ runtime }: Props) {
  // 只显示 API 中真实存在的字段
  const present = FIELDS.filter((f) => isNumber(runtime[f.key]));
  if (present.length === 0) return <span className="muted">{EMPTY}</span>;
  return (
    <Descriptions column={{ xs: 1, sm: 2 }} size="small" colon={false}>
      {present.map((f) => (
        <Descriptions.Item key={f.key} label={<span>{f.zh} <span className="muted">{f.en}</span></span>}>
          <strong className={f.key === 'total_seconds' ? 'runtime-total' : undefined}>
            {formatSeconds(runtime[f.key])}
          </strong>
        </Descriptions.Item>
      ))}
    </Descriptions>
  );
}
