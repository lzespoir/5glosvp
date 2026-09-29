import { useMemo, useState } from 'react';
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Select, Space, Spin, Statistic, Table, Tabs, Tag, Typography } from 'antd';
import { CheckCircleOutlined, ExperimentOutlined, SafetyCertificateOutlined } from '@ant-design/icons';

import { useAcceptanceMapping, useMaterializeScenario, useScenarioCatalog, useScenarioCoverage, useScenarioPreview, useScenarioTaxonomy } from '../../api/scenarioSystem';
import { useBackends } from '../../api/backends';
import { useScenarios } from '../../api/scenarios';
import { ScenarioCard } from './ScenarioCard';
import { PageHeader } from '../../components/PageHeader';
import { ErrorState } from '../../components/ErrorState';
import type { ScenarioDefinition } from '../../types/scenarioSystem';

const statusLabel: Record<string, string> = {
  VALID_EXECUTABLE: '有效·可执行',
  VALID_NOT_EXECUTABLE: '有效·待接入',
  INVALID_COMBINATION: '无效组合',
  REQUIRES_EXTERNAL_ASSET: '需要外部资产',
};

const countCards = [
  ['theoretical_count', '理论组合'],
  ['valid_count', '有效组合'],
  ['executable_count', '可执行组合'],
  ['requires_external_asset_count', '需要外部模型/数据'],
  ['materialized_count', '已实例化'],
  ['verified_count', '已验证'],
] as const;

export function ScenariosPage() {
  const taxonomy = useScenarioTaxonomy();
  const catalog = useScenarioCatalog();
  const coverage = useScenarioCoverage();
  const acceptance = useAcceptanceMapping();
  const legacy = useScenarios();
  const backends = useBackends();
  const materialize = useMaterializeScenario();
  const [selection, setSelection] = useState<Record<string, string[]>>({});
  const [selected, setSelected] = useState<ScenarioDefinition | null>(null);
  const preview = useScenarioPreview(selection, taxonomy.isSuccess);
  const options = taxonomy.data?.dimensions ?? [];
  const previewCounts = preview.data?.counts ?? { theoretical_count: 0, valid_count: 0, executable_count: 0, requires_external_asset_count: 0, materialized_count: 0, verified_count: 0, invalid_count: 0 };
  const backendById = new Map((backends.data ?? []).map((b) => [b.id, b]));
  const legacyLoaded = backends.isSuccess;
  const columns = useMemo(() => [
    { title: 'Scenario ID', dataIndex: 'scenario_id', key: 'scenario_id' },
    { title: '业务语义', dataIndex: 'name_zh', key: 'name_zh' },
    { title: 'Family', dataIndex: 'scenario_family', key: 'scenario_family' },
    { title: '状态', dataIndex: 'compatibility_status', key: 'compatibility_status', render: (value: string) => <Tag color={value === 'VALID_EXECUTABLE' ? 'green' : 'gold'}>{statusLabel[value] ?? value}</Tag> },
  ], []);

  if (taxonomy.isLoading || catalog.isLoading || coverage.isLoading || acceptance.isLoading) return <Spin fullscreen description="加载场景体系 Loading scenario system" />;
  if (taxonomy.isError || catalog.isError || coverage.isError || acceptance.isError) return <ErrorState error={taxonomy.error ?? catalog.error ?? coverage.error ?? acceptance.error} onRetry={() => { void taxonomy.refetch(); void catalog.refetch(); void coverage.refetch(); void acceptance.refetch(); }} />;

  return (
    <>
      <PageHeader titleZh="场景中心" titleEn="Scenario Center" subtitle="可组合、可追溯的 5G 业务场景体系 · Scenario taxonomy, combinations and coverage" />
      <Alert className="section-bottom" type="info" showIcon title="计数语义" description="理论组合、有效组合、可执行组合、已实例化、已执行、已验证和验收证据分开统计；百余定义不等于百余场景已完成系统级仿真验证。" />
      <Tabs items={[
        {
          key: 'overview', label: '场景总览 Overview', children: (
            <Row gutter={[16, 16]}>
              {countCards.map(([key, label]) => <Col key={key} xs={12} md={8} xl={4}><Card><Statistic title={label} value={coverage.data?.counts[key] ?? 0} /></Card></Col>)}
              <Col span={24}><Card title="Taxonomy V0.1"><Space wrap>{options.map((dimension) => <Tag key={dimension.key} color="blue">{dimension.label_zh} {dimension.options.length} 项</Tag>)}</Space><Typography.Paragraph className="section-top">已 materialize {catalog.data?.total ?? 0} 个具有不同业务语义的 definition；seed 仅属于 Scenario Instance。</Typography.Paragraph></Card></Col>
            </Row>
          ),
        },
        {
          key: 'builder', label: '场景组合器 Builder', children: (
            <Card title="多维组合选择 Multi-dimensional selection">
              <Row gutter={[16, 16]}>
                {options.map((dimension) => <Col key={dimension.key} xs={24} md={12} xl={8}><Typography.Text strong>{dimension.label_zh} / {dimension.label_en}</Typography.Text><Select mode="multiple" allowClear style={{ width: '100%', marginTop: 8 }} placeholder="全部 / All" value={selection[dimension.key]} onChange={(value) => setSelection((previous) => ({ ...previous, [dimension.key]: value }))} options={dimension.options.map((option) => ({ value: option.value, label: option.label_zh + ' · ' + option.status }))} /></Col>)}
              </Row>
              <Row gutter={[16, 16]} className="section-top">{countCards.slice(0, 4).map(([key, label]) => <Col key={key} xs={12} md={6}><Statistic title={label} value={previewCounts[key] ?? 0} /></Col>)}</Row>
              {preview.data?.truncated && <Alert className="section-top" type="warning" showIcon title="组合预览已截断" description="计数是完整计算结果，表格只展示前 100 个组合以保持页面可用。" />}
              <Table className="section-top" rowKey="scenario_id" size="small" pagination={{ pageSize: 8 }} dataSource={preview.data?.combinations ?? []} columns={columns} onRow={(record) => ({ onClick: () => setSelected(record) })} />
            </Card>
          ),
        },
        {
          key: 'catalog', label: '场景库 Catalog', children: (
            <Card title={'语义定义 ' + (catalog.data?.total ?? 0) + ' 个 / Semantic definitions'}>
              <Table rowKey="scenario_id" dataSource={catalog.data?.items ?? []} columns={columns} pagination={{ pageSize: 10 }} onRow={(record) => ({ onClick: () => setSelected(record) })} />
            </Card>
          ),
        },
        {
          key: 'coverage', label: '覆盖矩阵 Coverage', children: (
            <Card title="Family × Optimization Problem">
              <Table rowKey={(record) => record.row + '-' + record.column} dataSource={coverage.data?.matrix ?? []} columns={[{ title: 'Family', dataIndex: 'row' }, { title: '优化问题', dataIndex: 'column' }, { title: '有效', dataIndex: ['counts', 'valid_count'] }, { title: '可执行', dataIndex: ['counts', 'executable_count'] }, { title: '已验证', dataIndex: ['counts', 'verified_count'] }]} pagination={{ pageSize: 12 }} />
            </Card>
          ),
        },
        {
          key: 'acceptance', label: '验收映射 Acceptance', children: (
            <Row gutter={[16, 16]}>{(acceptance.data ?? []).map((item) => <Col key={item.key} xs={24} xl={12}><Card title={item.title_zh} extra={<Tag>{item.status}</Tag>}><Typography.Paragraph>{item.note_zh}</Typography.Paragraph><Space wrap>{item.evidence.map((evidence) => <Tag key={evidence} icon={<SafetyCertificateOutlined />}>{evidence}</Tag>)}</Space></Card></Col>)}</Row>
          ),
        },
      ]} />
      {selected && <Card className="section-top" title="场景详情 Scenario Detail" extra={<Button icon={<ExperimentOutlined />} onClick={() => materialize.mutate(selected.scenario_id)} loading={materialize.isPending}>用此场景创建实验 Workspace</Button>}>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="Scenario ID">{selected.scenario_id}</Descriptions.Item>
          <Descriptions.Item label="Version / Hash">{selected.version} / {selected.scenario_definition_hash.slice(0, 16)}…</Descriptions.Item>
          <Descriptions.Item label="业务语义" span={2}>{selected.name_zh}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag icon={<CheckCircleOutlined />}>{statusLabel[selected.compatibility_status] ?? selected.compatibility_status}</Tag></Descriptions.Item>
          <Descriptions.Item label="支持问题">{selected.supported_problem_types.join(', ')}</Descriptions.Item>
          <Descriptions.Item label="组合维度" span={2}>{Object.entries(selected.dimensions).map(([key, value]) => <Tag key={key}>{key}: {value}</Tag>)}</Descriptions.Item>
        </Descriptions>
      </Card>}
      {materialize.data && <Alert className="section-top" type="success" showIcon title="Experiment Workspace identity 已生成" description={materialize.data.message_zh + ' scenario_instance_id=' + materialize.data.scenario_instance.scenario_instance_id} />}
      <Card className="section-top" title="既有可运行仿真场景 Existing runnable simulation scenarios">
        {legacy.isLoading ? <Spin /> : legacy.isError ? <Alert type="warning" title="既有仿真场景暂不可用" /> : legacy.data?.length ? <Row gutter={[16, 16]}>{legacy.data.map((scenario) => <Col key={scenario.scenario_id} xs={24} xl={12}><ScenarioCard scenario={scenario} backend={backendById.get(scenario.backend)} backendsLoaded={legacyLoaded} /></Col>)}</Row> : <Empty description="暂无既有仿真场景" />}
      </Card>
    </>
  );
}
