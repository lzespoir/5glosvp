import { useState } from 'react';
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Select, Space, Spin, Statistic, Table, Tag, Typography, message } from 'antd';
import { useNavigate } from 'react-router-dom';

import { useScenarioTaxonomy } from '../../api/scenarioSystem';
import { scenarioCandidatesApi, type CandidatePreview, type ScenarioCandidate } from '../../api/scenarioCandidates';
import { PageHeader } from '../../components/PageHeader';
import { ErrorState } from '../../components/ErrorState';

const statusLabel: Record<string, string> = {
  VALID_EXECUTABLE: '有效 · 规则标记可执行',
  VALID_NOT_EXECUTABLE: '有效 · 待接入模型',
  INVALID_COMBINATION: '无效组合',
  REQUIRES_EXTERNAL_ASSET: '依赖外部模型/数据',
};

export function ScenariosPage() {
  const navigate = useNavigate();
  const [messageApi, context] = message.useMessage();
  const taxonomy = useScenarioTaxonomy();
  const [selection, setSelection] = useState<Record<string, string[]>>({});
  const [preview, setPreview] = useState<CandidatePreview | null>(null);
  const [selected, setSelected] = useState<ScenarioCandidate | null>(null);
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [pendingFilters, setPendingFilters] = useState<Record<string, string>>({});
  const [previewLoading, setPreviewLoading] = useState(false);
  const [promoteLoading, setPromoteLoading] = useState(false);
  const dimensions = taxonomy.data?.dimensions ?? [];
  const complete = dimensions.length > 0 && dimensions.every((dimension) => (selection[dimension.key]?.length ?? 0) > 0);

  const generate = async () => {
    setPreviewLoading(true);
    setSelected(null);
    setOffset(0);
    try {
      setPreview(await scenarioCandidatesApi.preview(selection, { offset: 0, limit: 20, filters }));
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const code = (error as { code?: string })?.code ?? (typeof detail === 'string' ? detail : '');
      messageApi.error(code === 'CANDIDATE_SPACE_TOO_LARGE' || code === 'HTTP_422' ? '候选空间过大或筛选条件无效，请缩小范围后重试。' : '候选预览失败，请检查所选范围后重试。');
      setPreview(null);
    } finally { setPreviewLoading(false); }
  };

  const loadPage = async (nextOffset: number, nextFilters = filters, expectedQueryHash?: string) => {
    setPreviewLoading(true);
    try {
      const next = await scenarioCandidatesApi.preview(selection, { offset: nextOffset, limit: 20, filters: nextFilters, query_hash: expectedQueryHash });
      setPreview(next);
      setOffset(nextOffset);
      setFilters(nextFilters);
      setSelected((previous) => next.items.find((item) => item.candidate_id === previous?.candidate_id) ?? previous);
    } catch {
      messageApi.error('候选列表加载失败，查询条件可能已变化，请重新生成预览。');
    } finally { setPreviewLoading(false); }
  };

  const promote = async () => {
    if (!selected) return;
    setPromoteLoading(true);
    try {
      const scenario = await scenarioCandidatesApi.promote(selected);
      messageApi.success('候选已显式保存为场景库中的 DRAFT 定义；尚未配置网络或创建实验。');
      navigate('/scenarios/' + scenario.scenario_id);
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const code = (error as { code?: string })?.code ?? (typeof detail === 'string' ? detail : '');
      messageApi.error(code === 'CANDIDATE_ALREADY_CONFIGURED' || code === 'HTTP_409' ? '该候选可能已保存，或查询已过期；请刷新候选后重试。' : '保存失败，候选身份校验未通过。');
    }
    finally { setPromoteLoading(false); }
  };

  if (taxonomy.isLoading) return <Spin fullscreen description="加载场景维度" />;
  if (taxonomy.isError) return <ErrorState error={taxonomy.error} onRetry={() => { void taxonomy.refetch(); }} />;

  const columns = [
    { title: '候选 ID', dataIndex: 'candidate_id', key: 'candidate_id' },
    { title: '业务语义', dataIndex: 'name_zh', key: 'name_zh' },
    { title: 'Family', dataIndex: 'scenario_family', key: 'scenario_family' },
    { title: '支持状态', dataIndex: 'compatibility_status', key: 'compatibility_status', render: (value: string) => <Tag color={value === 'VALID_EXECUTABLE' ? 'green' : 'gold'}>{statusLabel[value] ?? value}</Tag> },
  ];

  return <>
    {context}
    <PageHeader titleZh="候选场景组合器" titleEn="Scenario Candidate Builder" subtitle="候选空间只用于筛选与预览；保存后才成为场景库中的配置定义。" />
    <Alert className="section-bottom" type="warning" showIcon title="候选 ≠ 已配置场景 ≠ 实验" description="候选配置仅用于辅助创建场景。候选不会自动进入场景库，也不会计入已配置场景或验收场景数量。预览在内存中计算；只有显式保存才新增一个 DRAFT 定义。" />
    <Card title="选择候选空间" extra={<Button type="primary" onClick={() => void generate()} disabled={!complete} loading={previewLoading}>生成候选预览</Button>}>
      <Typography.Paragraph type="secondary">每个维度至少选择一项。单次候选探索最多检查 5,000 个组合，这是请求安全上限，不是平台场景容量；候选结果使用服务端分页浏览。</Typography.Paragraph>
      <Row gutter={[16, 16]}>
        {dimensions.map((dimension) => <Col key={dimension.key} xs={24} md={12} xl={8}>
          <Typography.Text strong>{dimension.label_zh} / {dimension.label_en}</Typography.Text>
          <Select mode="multiple" allowClear style={{ width: '100%', marginTop: 8 }} placeholder="选择至少一项" value={selection[dimension.key] ?? []} onChange={(value) => { setSelection((previous) => ({ ...previous, [dimension.key]: value })); setPreview(null); setSelected(null); setOffset(0); setFilters({}); setPendingFilters({}); }} options={dimension.options.map((option) => ({ value: option.value, label: option.label_zh + ' · ' + option.status }))} />
        </Col>)}
      </Row>
    </Card>

    {complete && <Card className="section-top" title="候选结果筛选" extra={<Button onClick={() => void loadPage(0, pendingFilters)}>应用筛选</Button>}>
      <Row gutter={[16, 12]}>{dimensions.filter((dimension) => (selection[dimension.key]?.length ?? 0) > 1).map((dimension) => <Col key={dimension.key} xs={24} md={12} xl={8}>
        <Typography.Text>{dimension.label_zh}</Typography.Text>
        <Select allowClear style={{ width: '100%', marginTop: 6 }} placeholder="全部已选项" value={pendingFilters[dimension.key] || undefined} onChange={(value) => setPendingFilters((previous) => { const next = { ...previous }; if (value) next[dimension.key] = value; else delete next[dimension.key]; return next; })} options={(selection[dimension.key] ?? []).map((value) => ({ value, label: dimension.options.find((option) => option.value === value)?.label_zh ?? value }))} />
      </Col>)}</Row>
      <Typography.Paragraph className="section-top" type="secondary">筛选只影响候选预览，不会保存或改变候选身份。</Typography.Paragraph>
    </Card>}

    {preview && <>
      <Row gutter={[12, 12]} className="section-top">
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="所选理论组合" value={preview.theoretical_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="有效候选总数" value={preview.valid_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="当前筛选结果" value={preview.filtered_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="无效组合" value={preview.invalid_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="规则标记可执行候选" value={preview.executable_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="依赖外部资产候选" value={preview.external_dependency_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="已保存场景变化" value={preview.configured_count_changed ? '是' : '否'} /></Card></Col>
      </Row>
      <Typography.Paragraph className="section-top" type="secondary">“规则标记可执行”仅表示 Day12 组合规则分类，不表示 Day15 网络配置完整、真实实验已运行或实验结果已验证。</Typography.Paragraph>
      {preview.total === 0 ? <Empty className="section-top" description="当前选择与筛选条件没有有效候选" /> : <Card className="section-top" title={`候选预览 · ${preview.total} 条（未保存）`}>
        <Table rowKey="candidate_id" size="small" loading={previewLoading} pagination={{ current: Math.floor(offset / preview.limit) + 1, pageSize: preview.limit, total: preview.total, showSizeChanger: false, onChange: (page) => void loadPage((page - 1) * preview.limit, filters, preview.query_hash) }} dataSource={preview.items} columns={columns} rowSelection={{ type: 'radio', selectedRowKeys: selected ? [selected.candidate_id] : [], onChange: (_keys, rows) => setSelected(rows[0] ?? null) }} onRow={(record) => ({ onClick: () => setSelected(record) })} />
      </Card>}
    </>}

    {selected && <Card className="section-top" title="候选详情" extra={<Button type="primary" onClick={() => void promote()} loading={promoteLoading}>显式保存到场景库</Button>}>
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="候选 ID">{selected.candidate_id}</Descriptions.Item>
        <Descriptions.Item label="Taxonomy">{selected.taxonomy_version}</Descriptions.Item>
        <Descriptions.Item label="业务语义" span={2}>{selected.name_zh} / {selected.name_en}</Descriptions.Item>
        <Descriptions.Item label="候选状态">{statusLabel[selected.compatibility_status] ?? selected.compatibility_status}</Descriptions.Item>
        <Descriptions.Item label="验收资格"><Tag color="default">无 · 候选不构成验收证据</Tag></Descriptions.Item>
        <Descriptions.Item label="维度" span={2}>{Object.entries(selected.dimensions).map(([key, value]) => <Tag key={key}>{key}: {value}</Tag>)}</Descriptions.Item>
      </Descriptions>
      <Typography.Paragraph className="section-top" type="secondary">保存动作只创建带候选来源与 lineage 的 DRAFT 定义。后续仍需进入场景编辑器补全物理网络配置并执行独立验证。</Typography.Paragraph>
    </Card>}
    <Space className="section-top"><Button onClick={() => navigate('/scenarios')}>打开已配置场景库</Button></Space>
  </>;
}
