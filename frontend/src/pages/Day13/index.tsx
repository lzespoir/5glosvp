import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, Card, Col, Descriptions, Form, Input, InputNumber, Row, Select, Space, Spin, Statistic, Table, Tabs, Tag, Typography } from 'antd';
import { EnvironmentOutlined, SafetyCertificateOutlined } from '@ant-design/icons';

import { useAMatrixLibraries, useAMatrixPattern, useAMatrixProfiles, useUETwinQuery } from '../../api/day13';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import type { AMatrixPattern, AMatrixProfile } from '../../types/day13';

function Heatmap({ pattern }: { pattern: AMatrixPattern }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const rows = pattern.normalized_response.length;
    const cols = pattern.normalized_response[0]?.length ?? 0;
    const cellW = canvas.width / cols;
    const cellH = canvas.height / rows;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pattern.normalized_response.forEach((row, r) => row.forEach((value, c) => {
      const hue = 240 - Math.max(0, Math.min(1, value)) * 240;
      ctx.fillStyle = `hsl(${hue} 85% 48%)`;
      ctx.fillRect(c * cellW, r * cellH, cellW + 0.4, cellH + 0.4);
    }));
  }, [pattern]);
  return <div><canvas ref={ref} width={720} height={360} style={{ width: '100%', height: 360, imageRendering: 'pixelated', border: '1px solid #d9d9d9', borderRadius: 6 }} aria-label="91×72 normalized relative beam response heatmap" /><Space style={{ width: '100%', justifyContent: 'space-between' }}><Typography.Text type="secondary">Elevation -90° → +90°（上到下）</Typography.Text><Typography.Text type="secondary">Azimuth 0° → 355°</Typography.Text></Space></div>;
}

function profileOptions(profiles: AMatrixProfile[]) {
  return profiles.map((profile) => ({ value: profile.id, label: `${profile.alias} · ${profile.library}/${profile.beam_type}` }));
}

export function Day13Page() {
  const libraries = useAMatrixLibraries();
  const profiles = useAMatrixProfiles();
  const [profileId, setProfileId] = useState('');
  const [beamId, setBeamId] = useState(0);
  const selectedProfile = (profiles.data ?? []).find((profile) => profile.id === profileId) ?? profiles.data?.[0];
  const activeProfileId = selectedProfile?.id ?? '';
  const activeBeamId = selectedProfile?.beam_ids.includes(beamId) ? beamId : (selectedProfile?.beam_ids[0] ?? 0);
  const entryKey = selectedProfile?.keys_by_beam[String(activeBeamId)] ?? selectedProfile?.entry_key ?? '';
  const pattern = useAMatrixPattern(selectedProfile?.library ?? 'spread', selectedProfile?.beam_type ?? 'SSB', entryKey);
  const ueTwin = useUETwinQuery();
  const [form] = Form.useForm();

  useEffect(() => { if (!profileId && profiles.data?.[0]) setProfileId(profiles.data[0].id); }, [profileId, profiles.data]);
  useEffect(() => { if (selectedProfile && !selectedProfile.beam_ids.includes(beamId)) setBeamId(selectedProfile.beam_ids[0] ?? 0); }, [selectedProfile, beamId]);

  if (libraries.isLoading || profiles.isLoading) return <Spin fullscreen description="加载 A-Matrix / UE Twin" />;
  if (libraries.isError || profiles.isError) return <ErrorState error={libraries.error ?? profiles.error} onRetry={() => { void libraries.refetch(); void profiles.refetch(); }} />;

  const submitUETwin = (values: Record<string, unknown>) => {
    ueTwin.mutate({
      ue_id: values.ue_id,
      aau_id: values.aau_id,
      profile_id: activeProfileId,
      serving_cell_id: values.serving_cell_id,
      neighbor_cell_ids: String(values.neighbor_cell_ids ?? '').split(',').map((value) => value.trim()).filter(Boolean),
      aau_position: { x: values.ax, y: values.ay, z: values.az, coordinate_system: 'SIONNA_SCENE_CARTESIAN', source: 'DAY13_UI' },
      ue_position: { x: values.ux, y: values.uy, z: values.uz, coordinate_system: 'SIONNA_SCENE_CARTESIAN', source: 'DAY13_UI' },
    });
  };

  return <>
    <PageHeader titleZh="A 矩阵与 UE Twin" titleEn="A-Matrix & UE Twin Radio Geometry" subtitle="真实 A-Matrix 的归一化相对方向响应、AAU↔UE 几何和多波束观察" extra={<Button type="primary"><Link to="/radio-observability">进入多小区 Radio View</Link></Button>} />
    <Alert type="warning" showIcon icon={<SafetyCertificateOutlined />} title="绝对无线 KPI 尚未校准" description="当前仅提供归一化相对波束响应、空间几何和相对波束排序；不将 normalized response 解释为 dBm、dBi、绝对 RSRP 或绝对 SINR。" />
    <Tabs className="section-top" items={[{
      key: 'explorer', label: 'A 矩阵 / 波束方向图', children: <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}><Card title="数据选择 Library / Profile / Beam">
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Select value={activeProfileId} options={profileOptions(profiles.data ?? [])} onChange={setProfileId} style={{ width: '100%' }} />
            <Select value={activeBeamId} options={(selectedProfile?.beam_ids ?? []).map((value) => ({ value, label: `Beam ${value}` }))} onChange={setBeamId} style={{ width: '100%' }} />
            {selectedProfile && <Descriptions size="small" column={1} bordered><Descriptions.Item label="AAU / Profile">{selectedProfile.aau_type} / {selectedProfile.alias}</Descriptions.Item><Descriptions.Item label="Beam family">{selectedProfile.library}</Descriptions.Item><Descriptions.Item label="Entry key">{entryKey}</Descriptions.Item><Descriptions.Item label="Mapping status">CONFIRMED_BY_PROFILE</Descriptions.Item></Descriptions>}
          </Space>
        </Card><Card title="检测到的 A-Matrix 库"><Space orientation="vertical" style={{ width: '100%' }}>{(libraries.data ?? []).map((item) => <Space key={item.library_id}><Tag color="blue">{item.library_id}</Tag><span>{item.family}</span><Typography.Text type="secondary">{item.entry_count} entries</Typography.Text></Space>)}</Space></Card></Col>
        <Col xs={24} xl={16}><Card title="归一化相对响应 · 91×72 Angular Grid">
          {pattern.isLoading ? <Spin /> : pattern.isError ? <Alert type="error" title="方向图加载失败" /> : pattern.data ? <><Heatmap pattern={pattern.data} /><Space wrap className="section-top"><Tag color="green">normalize: peak → 1</Tag><Tag>lookup: nearest-grid</Tag><Tag>axis: elevation × azimuth</Tag><Tag>source: {pattern.data.angular_grid.convention_source}</Tag></Space><Typography.Paragraph type="secondary" className="section-top">当前显示值为 normalized relative response；场幅度按 sqrt(max(response, 0)) 供兼容 Sionna pattern consumer 使用。</Typography.Paragraph></> : null}
        </Card></Col>
      </Row>,
    }, {
      key: 'ue-twin', label: 'UE Twin 无线几何', children: <Row gutter={[16, 16]}>
        <Col xs={24} xl={9}><Card title="UE / AAU 查询"><Form form={form} layout="vertical" onFinish={submitUETwin} initialValues={{ ue_id: 'UE-D13-001', aau_id: 'AAU-D13-001', ax: 0, ay: 0, az: 10, ux: 20, uy: 0, uz: 1.5, serving_cell_id: 'CELL-1', neighbor_cell_ids: 'CELL-2,CELL-3' }}><Row gutter={8}><Col span={12}><Form.Item name="ue_id" label="UE ID"><Input /></Form.Item></Col><Col span={12}><Form.Item name="aau_id" label="AAU ID"><Input /></Form.Item></Col></Row><Form.Item name="serving_cell_id" label="Serving Cell"><Input /></Form.Item><Form.Item name="neighbor_cell_ids" label="Neighbor Cells"><Input /></Form.Item><Typography.Text strong>AAU position · Sionna Cartesian [m]</Typography.Text><Row gutter={8}>{['ax', 'ay', 'az'].map((name) => <Col span={8} key={name}><Form.Item name={name} label={name}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>)}</Row><Typography.Text strong>UE position · Sionna Cartesian [m]</Typography.Text><Row gutter={8}>{['ux', 'uy', 'uz'].map((name) => <Col span={8} key={name}><Form.Item name={name} label={name}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>)}</Row><Button type="primary" htmlType="submit" icon={<EnvironmentOutlined />} loading={ueTwin.isPending}>查询方向与相对波束响应</Button></Form></Card></Col>
        <Col xs={24} xl={15}>{ueTwin.data ? <><Card title="AAU ↔ UE 几何"><Row gutter={16}><Col span={8}><Statistic title="距离 / Distance" value={ueTwin.data.radio_geometry.distance_3d_m} precision={3} suffix="m" /></Col><Col span={8}><Statistic title="Azimuth" value={ueTwin.data.radio_geometry.azimuth_deg} precision={2} suffix="°" /></Col><Col span={8}><Statistic title="Elevation" value={ueTwin.data.radio_geometry.elevation_deg} precision={2} suffix="°" /></Col></Row><Descriptions className="section-top" size="small" column={2} bordered><Descriptions.Item label="Serving cell">{ueTwin.data.serving_cell_id ?? '未绑定'}</Descriptions.Item><Descriptions.Item label="Neighbor cells">{ueTwin.data.neighbor_cell_ids.join(', ') || '无'}</Descriptions.Item><Descriptions.Item label="Coordinate">{ueTwin.data.radio_geometry.coordinate_convention}</Descriptions.Item><Descriptions.Item label="Calibration"><Tag color="orange">{ueTwin.data.calibration_status}</Tag></Descriptions.Item></Descriptions></Card><Card className="section-top" title={<Space>相对波束响应 <Tag color="green">当前方向最强波束：Beam {ueTwin.data.strongest_relative_beam_id ?? '—'}</Tag></Space>}><Table rowKey="beam_id" size="small" pagination={false} dataSource={ueTwin.data.beam_observations} columns={[{ title: 'Rank', dataIndex: 'rank' }, { title: 'Beam', dataIndex: 'beam_id' }, { title: '归一化响应', dataIndex: 'normalized_response', render: (value: number) => value.toFixed(6) }, { title: 'Lookup', dataIndex: 'lookup_method' }]} /></Card></> : <Card><Typography.Paragraph>输入 AAU 与 UE 的 Sionna Cartesian 坐标后查询。这里展示的是 radio observation/context，不执行 handover、切换或绝对 KPI 计算。</Typography.Paragraph></Card>}</Col>
      </Row>,
    }]} />
  </>;
}
