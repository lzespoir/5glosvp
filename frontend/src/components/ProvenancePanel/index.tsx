import { Alert, Descriptions } from 'antd';

import type { ExperimentResponse } from '../../types/experiment';
import { EMPTY } from '../../utils/format';
import { ProvenanceTag } from '../ProvenanceTag';

function yesNo(v: boolean | null | undefined): string {
  if (v === true) return '是 Yes';
  if (v === false) return '否 No';
  return EMPTY;
}

export function ProvenancePanel({ experiment }: { experiment: ExperimentResponse }) {
  const p = experiment.provenance;
  const isFixture = p?.source_type === 'test_fixture';
  return (
    <>
      <Descriptions column={1} size="small">
        <Descriptions.Item label="数据类型 Data Type">
          {p ? <ProvenanceTag sourceType={p.source_type} /> : EMPTY}
        </Descriptions.Item>
        <Descriptions.Item label="仿真引擎 Engine">{p?.engine ?? EMPTY}</Descriptions.Item>
        <Descriptions.Item label="引擎版本 Version">{experiment.backend.version ?? EMPTY}</Descriptions.Item>
        <Descriptions.Item label="仿真生成 Generated">{yesNo(p?.generated)}</Descriptions.Item>
        <Descriptions.Item label="实测数据 Measured">{yesNo(p?.measured)}</Descriptions.Item>
        {p?.tag && <Descriptions.Item label="来源标记 Tag"><code>[{p.tag}]</code></Descriptions.Item>}
      </Descriptions>
      <Alert
        type="info"
        showIcon
        className="section"
        title={
          isFixture
            ? '当前结果为软件测试夹具数据（TEST FIXTURE），仅用于开发测试，不代表任何仿真或实测结果。'
            : '当前结果由 Sionna RT 仿真生成，不属于华为实测数据或运营商现网数据，不可作为最终项目验收实测证据。'
        }
      />
    </>
  );
}
