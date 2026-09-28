import { Alert, Card, Col, Row, Tag } from 'antd';
import { Link } from 'react-router-dom';

import type { SystemOptimizationResponse } from '../../types/systemOptimization';
import { NETWORK_THROUGHPUT } from '../../utils/system';
import {
  directionMeta,
  formatMbps,
  formatParameter,
  formatPercentSigned,
  kpiMeta,
  NO_IMPROVEMENT_EN,
  NO_IMPROVEMENT_ZH,
  outcomeClaim,
} from '../../utils/systemOptimization';

interface Props {
  optimization: SystemOptimizationResponse;
}

function experimentLink(id: string, optimizationId: string) {
  return (
    <Link to={`/system/experiments/${id}`} state={{ fromOptimization: optimizationId }}>
      <code>{id}</code>
    </Link>
  );
}

/** Baseline vs Best：所有数值直接来自后端 comparison，前端不计算 KPI 或目标值。 */
export function HeroComparison({ optimization: o }: Props) {
  const c = o.comparison;
  if (!c) return null;
  const pid = o.parameter.id;
  const network = c.kpi_changes.find((k) => k.kpi_id === NETWORK_THROUGHPUT);
  const secondary = c.kpi_changes.filter((k) => k.kpi_id !== NETWORK_THROUGHPUT);
  const claim = outcomeClaim(o);

  return (
    <Card className="section-bottom" data-testid="hero-comparison">
      <Row gutter={[24, 16]} align="middle">
        <Col xs={24} md={9}>
          <div className="section-label">BASELINE</div>
          <div className="hero-value">
            {o.parameter.name_en} = {formatParameter(c.baseline_parameters[pid])}
          </div>
          <div className="hero-kpi">{formatMbps(c.baseline_objective)}</div>
          <div className="muted">
            {c.baseline_candidate_id} · {experimentLink(c.baseline_experiment_id, o.optimization_id)}
          </div>
        </Col>
        <Col xs={24} md={6} className="hero-vs">
          <div className="hero-vs__label">VS</div>
          <Tag color={c.improved ? 'success' : 'default'} className="hero-delta" data-testid="hero-delta">
            Δ {formatPercentSigned(c.relative_improvement_percent)}
          </Tag>
          <div className="muted">{formatMbps(c.absolute_improvement, 3)}</div>
        </Col>
        <Col xs={24} md={9}>
          <div className="section-label">BEST CANDIDATE</div>
          <div className="hero-value">
            {o.parameter.name_en} = {formatParameter(c.best_parameters[pid])}
          </div>
          <div className="hero-kpi">{formatMbps(c.best_objective)}</div>
          <div className="muted">
            {c.best_candidate_id} · {experimentLink(c.best_experiment_id, o.optimization_id)}
          </div>
        </Col>
      </Row>
      <div className="section">
        {c.improved ? (
          <Alert type="success" showIcon title={claim} description="目标 KPI：Network Throughput（NETWORK_THROUGHPUT_V0_1）" />
        ) : (
          <Alert type="warning" showIcon title={NO_IMPROVEMENT_ZH} description={NO_IMPROVEMENT_EN} data-testid="no-improvement" />
        )}
      </div>
      <Row gutter={[16, 16]} className="section" data-testid="secondary-kpis">
        {[network, ...secondary].filter((k) => k !== undefined).map((k) => {
          const meta = kpiMeta(k.kpi_id);
          const dir = directionMeta(k.direction);
          const negative = c.negative_kpi_changes.includes(k.kpi_id);
          return (
            <Col xs={24} md={8} key={k.kpi_id}>
              <Card size="small" className={negative ? 'kpi-change kpi-change--negative' : 'kpi-change'}>
                <div className="muted">
                  {meta?.zh} {meta?.en}
                  {k.kpi_id === NETWORK_THROUGHPUT ? <Tag color="blue" className="tag-inline">Objective</Tag> : <Tag className="tag-inline">Secondary</Tag>}
                </div>
                <div className="kpi-change__values">
                  {formatMbps(k.baseline)} → {formatMbps(k.best)}
                </div>
                <Tag color={dir.color} data-testid={`kpi-direction-${k.kpi_id}`}>
                  {dir.symbol} {formatPercentSigned(k.relative_change_percent)} · {dir.en}
                </Tag>
              </Card>
            </Col>
          );
        })}
      </Row>
      {c.negative_kpi_changes.length > 0 && (
        <Alert
          type="warning"
          showIcon
          className="section"
          title="存在负向 trade-off / Negative trade-off"
          description={`最优候选使以下 KPI 下降：${c.negative_kpi_changes.map((id) => kpiMeta(id)?.en ?? id).join(', ')}`}
        />
      )}
    </Card>
  );
}
