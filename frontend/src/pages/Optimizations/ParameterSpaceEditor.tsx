import { Col, Form, Input, InputNumber, Row, Space, Tag } from 'antd';

import type { SystemParameterView } from '../../types/systemOptimization';
import { boundsText, formatParameter, MAX_SYSTEM_CANDIDATES } from '../../utils/systemOptimization';

export interface ContinuousRange {
  lower: number | null;
  upper: number | null;
}

interface Props {
  kind: 'continuous' | 'discrete' | null;
  parameter: SystemParameterView;
  baseline: number | undefined;
  range: ContinuousRange;
  onRange: (r: ContinuousRange) => void;
  rangeError: string | null;
  candidateText: string;
  onCandidateText: (t: string) => void;
  candidateError: string | null;
}

/** Schema 驱动的最小参数编辑器：只支持 Day 7 实际需要的 continuous / discrete。 */
export function ParameterSpaceEditor(p: Props) {
  const def = p.parameter.definition;
  const title = (
    <Space size={6}>
      参数空间 Parameter Space (<code>{def.id}</code>)
      <Tag>定义域 Domain {boundsText(def)}</Tag>
      <Tag>单位 Unit {def.unit}</Tag>
    </Space>
  );
  if (p.kind === null) {
    return (
      <Form.Item label={title} validateStatus="error" help="所选算法不支持该参数类型 / Algorithm cannot handle this parameter">
        <span className="muted">—</span>
      </Form.Item>
    );
  }
  if (p.kind === 'discrete') {
    return (
      <Form.Item
        label={<Space size={6}>{title}<Tag color="blue">离散 Discrete</Tag></Space>}
        validateStatus={p.candidateError ? 'error' : undefined}
        help={
          p.candidateError
          ?? `基线 Baseline = ${formatParameter(p.baseline)}（场景配置，单独评估）· 最多 ${MAX_SYSTEM_CANDIDATES} 个候选`
        }
      >
        <Input aria-label="Candidate values" value={p.candidateText} onChange={(e) => p.onCandidateText(e.target.value)} />
      </Form.Item>
    );
  }
  const [recLower, recUpper] = p.parameter.recommended_search_bounds;
  return (
    <Form.Item
      label={<Space size={6}>{title}<Tag color="purple">连续 Continuous</Tag></Space>}
      validateStatus={p.rangeError ? 'error' : undefined}
      help={
        p.rangeError
        ?? `推荐区间 Recommended [${recLower}, ${recUpper}] · ${p.parameter.recommended_search_bounds_source}`
      }
      data-testid="continuous-editor"
    >
      <Row gutter={12}>
        <Col span={8}>
          <div className="muted">下界 Lower</div>
          <InputNumber aria-label="Lower bound" style={{ width: '100%' }} step={0.01} value={p.range.lower}
            onChange={(v) => p.onRange({ ...p.range, lower: v })} />
        </Col>
        <Col span={8}>
          <div className="muted">上界 Upper</div>
          <InputNumber aria-label="Upper bound" style={{ width: '100%' }} step={0.01} value={p.range.upper}
            onChange={(v) => p.onRange({ ...p.range, upper: v })} />
        </Col>
        <Col span={8}>
          <div className="muted">起点 Default（基线 Baseline）</div>
          <InputNumber aria-label="Default value" style={{ width: '100%' }} value={p.baseline ?? null} disabled />
        </Col>
      </Row>
    </Form.Item>
  );
}

/** 连续区间的表单提示；后端仍校验（只允许收窄推荐区间）。 */
export function continuousRangeError(r: ContinuousRange, recommended: number[]): string | null {
  if (r.lower === null || r.upper === null) return '需要上下界 / Lower and upper bounds required';
  if (!(r.lower < r.upper)) return '下界必须小于上界 / Lower must be below upper';
  const [lo = -Infinity, hi = Infinity] = recommended;
  if (r.lower < lo || r.upper > hi) return `只能收窄推荐区间 [${lo}, ${hi}] / Must stay within the recommended interval`;
  return null;
}
