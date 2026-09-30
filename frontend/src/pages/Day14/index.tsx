import { Alert, Card, Col, Descriptions, Row, Select, Space, Spin, Statistic, Table, Tag, Typography } from 'antd';
import { RadarChartOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useState } from 'react';

import { useRadioObservation, useRadioScenarios } from '../../api/radio';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';

export function Day14Page() {
  const scenarios = useRadioScenarios();
  const scenario = scenarios.data?.[0];
  const [ueId, setUeId] = useState('UE-D14-001');
  const observation = useRadioObservation(scenario?.scenario_id ?? '', ueId);

  if (scenarios.isLoading) return <Spin fullscreen description="加载多小区无线观测场景" />;
  if (scenarios.isError || !scenario) return <ErrorState error={scenarios.error} onRetry={() => { void scenarios.refetch(); }} />;

  const data = observation.data;
  const serving = data?.cells.find((cell) => cell.role === 'SERVING');
  return <>
    <PageHeader titleZh="多小区无线可观测性" titleEn="Multi-site Radio Observability" subtitle="Scenario → UE Twin → Radio View：服务小区、邻区、方向响应、功率分解与干扰解释" />
    <Alert type="warning" showIcon icon={<SafetyCertificateOutlined />} title="当前为未校准仿真观测" description="SIM_RECEIVED_POWER / SIM_SINR 只用于同一场景内的相对比较；不等同于实测 RSRP、绝对 SINR 或现网 KPI。A-Matrix 保持为归一化相对方向响应。" />
    <Card className="section-top" title={<Space><RadarChartOutlined />场景与 UE 选择</Space>}>
      <Space wrap>
        <Tag color="blue">{scenario.name_zh}</Tag>
        <Tag>{scenario.cell_count} cells / {scenario.ue_count} UEs</Tag>
        <Select value={ueId} onChange={setUeId} style={{ minWidth: 190 }} options={['UE-D14-001', 'UE-D14-002', 'UE-D14-003'].map((id) => ({ value: id, label: id }))} />
        <Tag color="orange">{scenario.status}</Tag>
      </Space>
    </Card>
    {observation.isLoading ? <Spin className="section-top" /> : observation.isError ? <div className="section-top"><ErrorState error={observation.error} onRetry={() => { void observation.refetch(); }} /></div> : data ? <>
      <Row gutter={[16, 16]} className="section-top">
        <Col xs={24} xl={8}><Card title="1 · UE 状态 / UE state"><Descriptions size="small" column={1} bordered><Descriptions.Item label="UE">{data.ue.ue_id}</Descriptions.Item><Descriptions.Item label="Position">[{data.ue.position.x}, {data.ue.position.y}, {data.ue.position.z}] m</Descriptions.Item><Descriptions.Item label="Mobility">{data.ue.mobility_state}</Descriptions.Item><Descriptions.Item label="Traffic">{data.ue.traffic_profile}</Descriptions.Item></Descriptions></Card></Col>
        <Col xs={24} xl={16}><Card title="2 · 多小区无线观测 / Multi-cell radio table"><Table rowKey={(row) => row.cell.cell_id} size="small" pagination={false} dataSource={data.cells} columns={[{ title: 'Cell', dataIndex: ['cell', 'cell_id'] }, { title: 'Role', dataIndex: 'role', render: (value: string) => <Tag color={value === 'SERVING' ? 'green' : 'blue'}>{value}</Tag> }, { title: 'Distance', render: (_: unknown, row) => `${row.geometry.distance_3d_m.toFixed(2)} m` }, { title: 'Az / El', render: (_: unknown, row) => `${row.geometry.azimuth_deg.toFixed(1)}° / ${row.geometry.elevation_deg.toFixed(1)}°` }, { title: 'SIM power', render: (_: unknown, row) => `${row.received_power.total.value?.toFixed(2) ?? '—'} dBm` }, { title: 'Beam', render: (_: unknown, row) => `#${row.strongest_relative_beam_id ?? '—'} · ${row.strongest_relative_response.value?.toFixed(4) ?? '—'}` }]} /></Card></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}><Card title="3 · Serving / Neighbor"><Statistic title="Serving cell" value={data.serving_neighbor.serving_cell_id} /><Descriptions className="section-top" size="small" column={1} bordered><Descriptions.Item label="Selection source">{data.serving_neighbor.serving_selection_source}</Descriptions.Item><Descriptions.Item label="Selection status">DECLARED_NOT_HANDOVER</Descriptions.Item><Descriptions.Item label="Neighbors">{data.serving_neighbor.neighbor_cell_ids.join(', ')}</Descriptions.Item></Descriptions><Table className="section-top" size="small" pagination={false} rowKey="cell_id" dataSource={data.serving_neighbor.ranked_neighbors} columns={[{ title: 'Neighbor', dataIndex: 'cell_id' }, { title: 'SIM power', dataIndex: 'sim_received_power_dbm', render: (value: number) => `${value.toFixed(2)} dBm` }]} /></Card></Col>
        <Col xs={24} xl={8}><Card title="4 · 功率与干扰分解">{serving ? <><Descriptions size="small" column={1} bordered><Descriptions.Item label="SIM_RECEIVED_POWER">{serving.received_power.total.value?.toFixed(3)} dBm</Descriptions.Item>{serving.received_power.components.map((item) => <Descriptions.Item key={item.metric_name} label={item.metric_name}>{item.value?.toFixed(3)} {item.unit}</Descriptions.Item>)}</Descriptions>{serving.interference && <Descriptions className="section-top" size="small" column={1} bordered><Descriptions.Item label="Aggregate interference">{serving.interference.aggregate_interference.value?.toFixed(3) ?? '—'} dBm</Descriptions.Item><Descriptions.Item label="Noise floor">{serving.interference.noise_floor.value?.toFixed(3)} dBm</Descriptions.Item><Descriptions.Item label="SIM_SINR">{serving.interference.sinr.value?.toFixed(3)} dB</Descriptions.Item></Descriptions>}</> : null}</Card></Col>
        <Col xs={24} xl={8}><Card title="5 · 解释与 provenance"><Typography.Paragraph><Tag color="orange">{data.calibration_status}</Tag> {data.absolute_radio_kpi_status}</Typography.Paragraph><Descriptions size="small" column={1} bordered><Descriptions.Item label="Backend">{data.identity.propagation_backend}</Descriptions.Item><Descriptions.Item label="A-Matrix hash">{data.identity.a_matrix_artifact_hashes[0]?.slice(0, 16)}…</Descriptions.Item><Descriptions.Item label="Lookup">{data.identity.lookup_method}</Descriptions.Item><Descriptions.Item label="Identity">{data.identity.identity_hash.slice(0, 16)}…</Descriptions.Item><Descriptions.Item label="Sionna executed">{data.provenance.sionna_executed ? '是' : '否'}</Descriptions.Item><Descriptions.Item label="Measured data">{data.provenance.measurement_data ? '是' : '否'}</Descriptions.Item></Descriptions></Card></Col>
      </Row>
    </> : null}
  </>;
}
