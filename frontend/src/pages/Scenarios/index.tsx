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
  const [previewLoading, setPreviewLoading] = useState(false);
  const [promoteLoading, setPromoteLoading] = useState(false);
  const dimensions = taxonomy.data?.dimensions ?? [];
  const complete = dimensions.length > 0 && dimensions.every((dimension) => (selection[dimension.key]?.length ?? 0) > 0);

  const generate = async () => {
    setPreviewLoading(true);
    setSelected(null);
    try {
      setPreview(await scenarioCandidatesApi.preview(selection, 50));
    } catch (error) {
      messageApi.error('候选预览失败：' + String(error));
      setPreview(null);
    } finally { setPreviewLoading(false); }
  };

  const promote = async () => {
    if (!selected) return;
    setPromoteLoading(true);
    try {
      const scenario = await scenarioCandidatesApi.promote(selected);
      messageApi.success('候选已显式保存为场景库中的 DRAFT 定义；尚未配置网络或创建实验。');
      navigate('/scenarios/' + scenario.scenario_id);
    } catch (error) { messageApi.error('保存失败：' + String(error)); }
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
    <Alert className="section-bottom" type="warning" showIcon title="候选 ≠ 已配置场景 ≠ 实验" description="预览在内存中计算，不写入场景库。只有显式保存后才新增一个 DRAFT 场景定义；这不会自动补齐环境、站点、小区、天线、UE，也不会创建或运行实验，更不构成验收证据。" />
    <Card title="选择候选空间" extra={<Button type="primary" onClick={() => void generate()} disabled={!complete} loading={previewLoading}>生成候选预览</Button>}>
      <Typography.Paragraph type="secondary">每个维度至少选择一项。系统限制一次最多枚举 5,000 个组合，表格最多展示 50 个有效候选。</Typography.Paragraph>
      <Row gutter={[16, 16]}>
        {dimensions.map((dimension) => <Col key={dimension.key} xs={24} md={12} xl={8}>
          <Typography.Text strong>{dimension.label_zh} / {dimension.label_en}</Typography.Text>
          <Select mode="multiple" allowClear style={{ width: '100%', marginTop: 8 }} placeholder="选择至少一项" value={selection[dimension.key] ?? []} onChange={(value) => { setSelection((previous) => ({ ...previous, [dimension.key]: value })); setPreview(null); setSelected(null); }} options={dimension.options.map((option) => ({ value: option.value, label: option.label_zh + ' · ' + option.status }))} />
        </Col>)}
      </Row>
    </Card>

    {preview && <>
      <Row gutter={[12, 12]} className="section-top">
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="所选理论组合" value={preview.theoretical_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="有效候选" value={preview.valid_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="无效组合" value={preview.invalid_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="规则标记可执行候选" value={preview.executable_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="依赖外部资产候选" value={preview.external_dependency_candidate_count} /></Card></Col>
        <Col xs={12} md={8} xl={4}><Card size="small"><Statistic title="已保存场景变化" value={preview.configured_count_changed ? '是' : '否'} /></Card></Col>
      </Row>
      <Typography.Paragraph className="section-top" type="secondary">“规则标记可执行”仅表示 Day12 组合规则分类，不表示 Day15 网络配置完整、真实实验已运行或实验结果已验证。</Typography.Paragraph>
      {preview.truncated && <Alert className="section-top" type="info" showIcon title="候选列表已截断" description={`有效候选共 ${preview.valid_candidate_count} 个；当前仅展示 ${preview.returned_count} 个。截断仅影响展示，不会自动保存剩余候选。`} />}
      {preview.items.length === 0 ? <Empty className="section-top" description="所选维度没有有效候选组合" /> : <Card className="section-top" title={`候选预览 · ${preview.returned_count} 条（未保存）`}>
        <Table rowKey="candidate_id" size="small" pagination={{ pageSize: 10 }} dataSource={preview.items} columns={columns} rowSelection={{ type: 'radio', selectedRowKeys: selected ? [selected.candidate_id] : [], onChange: (_keys, rows) => setSelected(rows[0] ?? null) }} onRow={(record) => ({ onClick: () => setSelected(record) })} />
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
