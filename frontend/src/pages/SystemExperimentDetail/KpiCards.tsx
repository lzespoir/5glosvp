import { InfoCircleOutlined } from '@ant-design/icons';
import { Card, Col, Row, Statistic, Tooltip } from 'antd';

import type { KpiResult } from '../../types/system';
import { EMPTY, isNumber } from '../../utils/format';
import { AVG_UE_THROUGHPUT, findKpi, NETWORK_THROUGHPUT, P5_UE_THROUGHPUT } from '../../utils/system';

interface Props {
  kpis: KpiResult[];
  ueCount: number | null;
  onOpen: (metricId: string) => void;
}

const CARDS: { id: string; zh: string; en: string }[] = [
  { id: NETWORK_THROUGHPUT, zh: '网络吞吐率', en: 'Network Throughput' },
  { id: AVG_UE_THROUGHPUT, zh: '平均 UE 吞吐率', en: 'Average UE Throughput' },
  { id: P5_UE_THROUGHPUT, zh: 'P5 UE 吞吐率', en: 'P5 UE Throughput' },
];

export function KpiCards({ kpis, ueCount, onOpen }: Props) {
  return (
    <Row gutter={[16, 16]}>
      {CARDS.map((c) => {
        const kpi = findKpi(kpis, c.id);
        const available = kpi?.available && isNumber(kpi.value);
        return (
          <Col xs={24} sm={12} xl={6} key={c.id}>
            <Card
              size="small"
              className="kpi-card clickable-card"
              hoverable
              onClick={() => onOpen(c.id)}
              data-testid={`kpi-card-${c.id}`}
            >
              <div className="kpi-card__title">
                {c.zh} <span className="muted">{c.en}</span>
                <InfoCircleOutlined className="kpi-card__info" />
              </div>
              {available ? (
                <Statistic value={kpi.value ?? undefined} precision={2} suffix={<span className="muted">{kpi.unit}</span>} />
              ) : (
                <Tooltip title={kpi?.unavailable_reason ?? '后端未返回 / Not returned'}>
                  <span className="kpi-card__value">{EMPTY}</span>
                  <div className="muted">Not Available</div>
                </Tooltip>
              )}
              <div className="muted kpi-card__meta">
                <code>{c.id}</code>
              </div>
            </Card>
          </Col>
        );
      })}
      <Col xs={24} sm={12} xl={6}>
        <Card size="small" className="kpi-card">
          <div className="kpi-card__title">
            UE 数量 <span className="muted">UE Count</span>
          </div>
          <Statistic value={ueCount ?? EMPTY} suffix={<span className="muted">UE</span>} />
          <div className="muted kpi-card__meta">含零吞吐率 UE · Includes zero-throughput UEs</div>
        </Card>
      </Col>
    </Row>
  );
}
