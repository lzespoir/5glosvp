import { Card, Skeleton, Space, Tag } from 'antd';
import { Link } from 'react-router-dom';

import { useExperiment } from '../../api/experiments';
import { ErrorState } from '../../components/ErrorState';
import { RadioMap } from '../../components/RadioMap';
import { formatObjective, formatPower } from '../../utils/optimization';

interface PanelProps {
  titleZh: string;
  titleEn: string;
  experimentId: string;
  txPower: number | undefined;
  objective: number | undefined;
  tag?: string;
}

function RadioMapPanel({ titleZh, titleEn, experimentId, txPower, objective, tag }: PanelProps) {
  const query = useExperiment(experimentId);
  return (
    <Card
      size="small"
      className="radio-map-card"
      title={<span>{titleZh} <span className="card-title-en">{titleEn}</span></span>}
      extra={
        <Space size={4}>
          {tag && <Tag color="green">{tag}</Tag>}
          <Link to={`/experiments/${experimentId}`}><code>{experimentId}</code></Link>
        </Space>
      }
    >
      <div className="before-after__meta">
        <span>TX Power <strong>{formatPower(txPower)}</strong></span>
        <span>Objective J <strong>{formatObjective(objective)}</strong></span>
      </div>
      {query.isLoading ? (
        <Skeleton.Image active className="radio-map__skeleton" />
      ) : query.isError || !query.data ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (
        <RadioMap experiment={query.data} maxHeight="46vh" />
      )}
    </Card>
  );
}

interface Props {
  baselineExperimentId: string;
  optimizedExperimentId: string;
  baselinePower: number | undefined;
  optimizedPower: number | undefined;
  baselineObjective: number | undefined;
  optimizedObjective: number | undefined;
  optimizedCandidateId: string;
}

/** 优化前后对比：两张图均来自各自实验的 radio_map.png artifact。 */
export function BeforeAfter(props: Props) {
  return (
    <div className="before-after">
      <RadioMapPanel
        titleZh="优化前"
        titleEn="Before · Baseline"
        experimentId={props.baselineExperimentId}
        txPower={props.baselinePower}
        objective={props.baselineObjective}
      />
      <RadioMapPanel
        titleZh="优化后"
        titleEn={`After · ${props.optimizedCandidateId}`}
        experimentId={props.optimizedExperimentId}
        txPower={props.optimizedPower}
        objective={props.optimizedObjective}
        tag="BEST"
      />
    </div>
  );
}
