import { Alert, Space } from 'antd';

import { toApiError } from '../../api/client';
import type { CompatibilityReport } from '../../types/algorithm';

interface Props {
  report: CompatibilityReport | undefined;
  error: unknown;
  checking: boolean;
}

/** POST /algorithms/{id}/validate 的即时结果；只展示后端给出的代码与消息。 */
export function CompatibilityFeedback({ report, error, checking }: Props) {
  if (error) {
    const e = toApiError(error);
    return (
      <Alert type="error" showIcon className="section" data-testid="compatibility-feedback"
        title={<span>参数空间无效 Invalid parameter space · <code>{e.code}</code></span>} description={e.messageEn} />
    );
  }
  if (!report) {
    return <Alert type="info" showIcon className="section" title={checking ? '检查兼容性… Checking compatibility' : '—'} />;
  }
  if (!report.compatible) {
    return (
      <Alert
        type="error"
        showIcon
        className="section"
        data-testid="compatibility-feedback"
        title="算法与问题不兼容 Incompatible"
        description={
          <Space orientation="vertical" size={2}>
            {report.errors.map((e) => (
              <span key={`${e.code}-${e.message}`}><code>{e.code}</code> {e.message}</span>
            ))}
          </Space>
        }
      />
    );
  }
  return (
    <Alert
      type={report.warnings.length ? 'warning' : 'success'}
      showIcon
      className="section"
      data-testid="compatibility-feedback"
      title="兼容 Compatible"
      description={report.warnings.length ? report.warnings.join(' · ') : undefined}
    />
  );
}
