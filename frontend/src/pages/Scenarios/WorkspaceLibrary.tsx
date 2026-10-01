import { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Empty, Input, Modal, Row, Select, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import { Link, useNavigate } from 'react-router-dom';
import { workspaceApi, type Counts, type Scenario, type WorkspaceCoverage } from '../../api/workspace';
import { PageHeader } from '../../components/PageHeader';

const countLabels: { key: keyof Counts; label: string }[] = [
  { key: 'configured_scenario_count', label: '已保存定义' }, { key: 'runnable_scenario_count', label: '可运行场景' },
  { key: 'executed_scenario_count', label: '已执行场景' }, { key: 'experiment_verified_count', label: '实验验证' },
  { key: 'acceptance_evidence_count', label: '验收证据' },
];

export function WorkspaceLibraryPage() {
  const navigate = useNavigate();
  const [messageApi, context] = message.useMessage();
  const [counts, setCounts] = useState<Counts | null>(null);
  const [coverage, setCoverage] = useState<WorkspaceCoverage | null>(null);
  const [items, setItems] = useState<Scenario[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [state, setState] = useState('');
  const [family, setFamily] = useState('');
  const [problem, setProblem] = useState('');
  const [traffic, setTraffic] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [newFamily, setNewFamily] = useState('custom');

  const reload = async () => {
    setLoading(true);
    try {
      const [page, nextCounts, nextCoverage] = await Promise.all([workspaceApi.list({ offset, limit: 20, search, state, family, problem, traffic }), workspaceApi.counts(), workspaceApi.coverage()]);
      setItems(page.items); setTotal(page.total); setCounts(nextCounts); setCoverage(nextCoverage); setError('');
    } catch (cause) { setError(String(cause)); }
    finally { setLoading(false); }
  };
  useEffect(() => { void reload(); }, [offset, search, state, family, problem, traffic]);

  const create = async () => {
    try { const created = await workspaceApi.create(name, newFamily); setCreateOpen(false); setName(''); navigate(`/scenarios/${created.scenario_id}`); }
    catch (cause) { messageApi.error(String(cause)); }
  };
  const clone = async (id: string) => {
    try { const copy = await workspaceApi.clone(id); messageApi.success('已复制独立配置版本'); navigate(`/scenarios/${copy.scenario_id}`); }
    catch (cause) { messageApi.error(String(cause)); }
  };
  const archive = (id: string) => Modal.confirm({ title: '归档场景定义？', content: '归档后不会删除既有定义或实例，页面默认可通过状态筛选找回。', onOk: async () => { await workspaceApi.archive(id); await reload(); } });

  return <>
    {context}
    <PageHeader titleZh="场景库" titleEn="Configured Scenario Library" subtitle="这里仅展示已经保存的业务配置；Day12 的组合候选不是已配置场景。" extra={<Space><Link to="/scenarios/advanced">高级组合视图</Link><Button type="primary" onClick={() => setCreateOpen(true)}>新建场景</Button></Space>} />
    <Alert type="info" showIcon className="section-bottom" title="定义、运行与验收分层" description="配置定义可保存并验证；目前 Day15 配置尚未接入实验执行器，因此“可运行/已执行/实验验证/验收证据”不会由保存或冻结实例自动增加。" />
    {error && <Alert type="error" showIcon title="场景库加载失败" description={error} className="section-bottom" />}
    <Row gutter={[12, 12]} className="section-bottom">{countLabels.map(({ key, label }) => <Col xs={12} md={8} xl={4} key={key}><Card size="small"><Statistic title={label} value={counts?.[key] ?? '—'} /></Card></Col>)}</Row>
    <Card className="section-bottom" title="已配置定义覆盖（仅持久化场景）" extra={<Tag color="blue">{coverage?.source ?? '加载中'}</Tag>}>
      <Typography.Paragraph type="secondary">候选组合与 Day12 first-N catalog 不参与该统计。草稿可以显示为已保存定义，但不代表网络配置完整、已运行或已经验收。</Typography.Paragraph>
      <Table size="small" rowKey={(row) => `${row.family}:${row.problem_type}`} pagination={false} dataSource={coverage?.matrix ?? []} locale={{ emptyText: '尚无已保存场景定义' }} columns={[{ title: 'Family', dataIndex: 'family' }, { title: '优化问题', dataIndex: 'problem_type', render: (value: string) => value === 'NETWORK_STRUCTURE' ? '网络结构' : value === 'USER_ACCESS' ? '用户接入' : '系统资源' }, { title: '已保存定义数', dataIndex: 'configured_count' }]} />
    </Card>
    <Card title="已配置场景定义" extra={<Space wrap><Input.Search aria-label="搜索场景" placeholder="名称 / ID" allowClear onSearch={(value) => { setOffset(0); setSearch(value); }} style={{ width: 190 }} /><Input aria-label="Family 筛选" placeholder="Family" value={family} onChange={(event) => { setOffset(0); setFamily(event.target.value); }} style={{ width: 110 }} /><Select aria-label="状态筛选" placeholder="状态" allowClear value={state || undefined} onChange={(value) => { setOffset(0); setState(value ?? ''); }} options={['DRAFT', 'VALID', 'INVALID', 'READY', 'ARCHIVED'].map((value) => ({ value, label: value }))} style={{ width: 130 }} /><Select aria-label="问题筛选" placeholder="优化问题" allowClear value={problem || undefined} onChange={(value) => { setOffset(0); setProblem(value ?? ''); }} options={['NETWORK_STRUCTURE', 'USER_ACCESS', 'SYSTEM_RESOURCE'].map((value) => ({ value, label: value }))} style={{ width: 160 }} /><Select aria-label="业务筛选" placeholder="Traffic" allowClear value={traffic || undefined} onChange={(value) => { setOffset(0); setTraffic(value ?? ''); }} options={['FULL_BUFFER', 'STATIC_DEMAND', 'TIME_SERIES', 'BEAM_SPACE_PREDICTION', 'MEASURED_TRAFFIC'].map((value) => ({ value, label: value }))} style={{ width: 180 }} /></Space>}>
      {items.length === 0 && !loading ? <Empty description="尚无已配置场景。可新建空白定义；组合候选请到高级组合视图查看。"><Button type="primary" onClick={() => setCreateOpen(true)}>创建第一个场景</Button></Empty> : <Table rowKey="scenario_id" loading={loading} dataSource={items} pagination={{ current: Math.floor(offset / 20) + 1, pageSize: 20, total, onChange: (page) => setOffset((page - 1) * 20) }} scroll={{ x: 950 }} columns={[
        { title: '名称 / ID', key: 'name', render: (_, row: Scenario) => <><Link to={`/scenarios/${row.scenario_id}`}>{row.name}</Link><div className="muted">{row.scenario_id}</div></> },
        { title: 'Family', dataIndex: 'family' }, { title: '来源 / 分类', key: 'classification', render: (_, row: Scenario) => <><Tag>{row.source}</Tag>{Object.entries(row.classification).slice(0, 2).map(([key, value]) => <Tag key={key}>{key}: {value}</Tag>)}</> }, { title: '环境', key: 'env', render: (_, row: Scenario) => row.environment?.environment_id ?? '未配置' },
        { title: '站点 / 小区 / UE', key: 'size', render: (_, row: Scenario) => `${row.sites.length} / ${row.cells.length} / ${row.ues.length}` },
        { title: '问题', key: 'problem', render: (_, row: Scenario) => row.optimization_problems.join(', ') || '未选择' },
        { title: '状态', dataIndex: 'state', render: (value: string) => <Tag color={value === 'VALID' ? 'green' : value === 'INVALID' ? 'red' : 'default'}>{value}</Tag> },
        { title: '版本', key: 'version', render: (_, row: Scenario) => <Typography.Text code>v{row.version} · {row.definition_hash.slice(0, 8)}</Typography.Text> },
        { title: '操作', key: 'action', render: (_, row: Scenario) => <Space><Link to={`/scenarios/${row.scenario_id}`}>打开</Link><Button type="link" onClick={() => void clone(row.scenario_id)}>复制</Button>{row.state !== 'ARCHIVED' && <Button type="link" danger onClick={() => archive(row.scenario_id)}>归档</Button>}</Space> },
      ]} />}
    </Card>
    <Modal title="新建场景定义" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => void create()} okText="创建空白定义" okButtonProps={{ disabled: !name.trim() }}><Space orientation="vertical" style={{ width: '100%' }}><Typography.Text>场景名称</Typography.Text><Input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：城区三站热点接入配置" /><Typography.Text>业务 Family</Typography.Text><Input value={newFamily} onChange={(event) => setNewFamily(event.target.value)} /><Typography.Text type="secondary">仅创建 DRAFT；不会产生运行、实验或验收证据。</Typography.Text></Space></Modal>
  </>;
}
