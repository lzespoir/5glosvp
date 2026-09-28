import { Descriptions, Tag } from 'antd';

import type { EvidenceDescriptor } from '../../types/algorithm';
import { acceptanceReasonLabel, verificationMeta } from '../../utils/algorithm';

/** 证据描述符：复核状态与验收资格分开展示（verification ≠ acceptance）。 */
export function EvidencePanel({ descriptor }: { descriptor: EvidenceDescriptor | null | undefined }) {
  if (!descriptor) return <span className="muted">—</span>;
  const v = verificationMeta(descriptor.verification_status);
  return (
    <Descriptions column={1} size="small" data-testid="evidence-panel">
      <Descriptions.Item label="证据 Evidence"><code>{descriptor.evidence_id}</code></Descriptions.Item>
      <Descriptions.Item label="复核 Verification">
        <Tag color={v.color}>{v.en}</Tag>{v.zh}
        {descriptor.verification_detail && <div className="muted">{descriptor.verification_detail}</div>}
      </Descriptions.Item>
      <Descriptions.Item label="独立复核 Independently Verified">{descriptor.verified ? 'Yes' : 'No'}</Descriptions.Item>
      <Descriptions.Item label="可作验收证据 Acceptance-eligible">
        <Tag>{descriptor.acceptance_eligible ? 'Yes' : 'No'}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="原因 Reasons">
        {descriptor.acceptance_reason.map((r) => <Tag key={r}>{acceptanceReasonLabel(r)}</Tag>)}
      </Descriptions.Item>
    </Descriptions>
  );
}
