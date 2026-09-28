import { Alert, Col, Empty, Row, Skeleton } from 'antd';

import { useBackends } from '../../api/backends';
import { useScenarios } from '../../api/scenarios';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import { ScenarioCard } from './ScenarioCard';

export function ScenariosPage() {
  const scenarios = useScenarios();
  const backends = useBackends();
  const backendById = new Map((backends.data ?? []).map((b) => [b.id, b]));
  const backendsLoaded = backends.isSuccess;

  return (
    <>
      <PageHeader
        titleZh="场景中心"
        titleEn="Scenario Center"
        subtitle="选择仿真场景并运行 Sionna RT 实验 · Select a scenario and run a simulation experiment"
      />
      {backends.isError && (
        <Alert
          type="error"
          showIcon
          className="section-bottom"
          title="无法获取仿真后端状态，已禁用运行实验。Backend status unavailable."
        />
      )}
      {scenarios.isLoading ? (
        <Row gutter={[16, 16]}>
          {[0, 1].map((i) => (
            <Col key={i} xs={24} xl={12}><Skeleton active paragraph={{ rows: 6 }} /></Col>
          ))}
        </Row>
      ) : scenarios.isError ? (
        <ErrorState error={scenarios.error} onRetry={() => scenarios.refetch()} />
      ) : (scenarios.data ?? []).length === 0 ? (
        <Empty description="暂无场景 / No scenarios" />
      ) : (
        <Row gutter={[16, 16]}>
          {(scenarios.data ?? []).map((s) => (
            <Col key={s.scenario_id} xs={24} xl={12}>
              <ScenarioCard scenario={s} backend={backendById.get(s.backend)} backendsLoaded={backendsLoaded} />
            </Col>
          ))}
        </Row>
      )}
    </>
  );
}
