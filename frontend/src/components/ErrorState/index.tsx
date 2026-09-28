import { Button, Result } from 'antd';

import { toApiError } from '../../api/client';

interface Props {
  error: unknown;
  onRetry?: () => void;
  compact?: boolean;
}

export function ErrorState({ error, onRetry, compact = false }: Props) {
  const apiError = toApiError(error);
  return (
    <Result
      status={apiError.status === 404 ? '404' : 'warning'}
      className={compact ? 'error-state error-state--compact' : 'error-state'}
      title={`${apiError.messageZh} / ${apiError.messageEn}`}
      subTitle={
        <span>
          <code>{apiError.code}</code>
          {typeof apiError.detail.reason === 'string' && <> · {apiError.detail.reason}</>}
        </span>
      }
      extra={onRetry && <Button onClick={onRetry}>重试 Retry</Button>}
    />
  );
}
