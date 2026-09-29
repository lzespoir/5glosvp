import { Alert, Button, Card, Checkbox, Empty, Select, Space, Table, Tag, Typography } from 'antd';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useComparisonRuns, useCreateComparison, usePreviewComparison, type ComparisonIntent } from '../../api/comparisons';

const { Title, Text } = Typography;
const intents: Array<{ value: ComparisonIntent; label: string }> = [
  { value: 'ALGORITHM_COMPARISON', label: '算法对比' }, { value: 'HYPERPARAMETER_COMPARISON', label: '超参数对比' },
  { value: 'CONFIGURATION_COMPARISON', label: '配置对比' }, { value: 'RUN_REPRODUCIBILITY', label: '运行复现' },
  { value: 'SCENARIO_ANALYSIS', label: '场景分析' }, { value: 'CUSTOM_ANALYSIS', label: '自定义分析' },
];

export function ComparisonsPage() {
  const runs = useComparisonRuns();
  const preview = usePreviewComparison();
  const create = useCreateComparison();
  const [selected, setSelected] = useState<string[]>([]);
  const [intent, setIntent] = useState<ComparisonIntent>('ALGORITHM_COMPARISON');
  const selectedRuns = useMemo(() => runs.data?.filter((run) => selected.includes(run.run_id)) ?? [], [runs.data, selected]);
  const request = { run_ids: selected, intent };
  return <Space orientation="vertical" size="large" style={{ width: '100%' }}>
    <div><Title level={2} style={{ marginBottom: 4 }}>对比分析</Title><Text type="secondary">由用户选择运行记录，先预览兼容性，再确认生成 Comparison 对象。</Text></div>
    <Alert type="info" showIcon title="对比分析不自动排名" description="不自动宣布胜者、不生成 A>B 或收益结论；不兼容记录仍可并列查看，但不会叠加不可比的指标。" />
    <Card title="1. 选择运行记录（至少 2 个）">
      {runs.isError ? <Empty description="运行记录暂不可用" /> :
        <Table rowKey="run_id" pagination={false} dataSource={runs.data ?? []} columns={[
          { title: '选择', render: (_: unknown, row: { run_id: string }) => <Checkbox checked={selected.includes(row.run_id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, row.run_id] : current.filter((id) => id !== row.run_id))} /> },
          { title: '运行 ID', dataIndex: 'run_id' }, { title: '算法', dataIndex: 'algorithm_id' }, { title: '版本', dataIndex: 'algorithm_version' },
          { title: '场景', dataIndex: 'scenario_id' }, { title: '状态', dataIndex: 'status' },
        ]} />}
    </Card>
    <Card title="2. 声明分析意图">
      <Space><Text>意图</Text><Select value={intent} options={intents} onChange={setIntent} style={{ width: 220 }} /><Button type="primary" disabled={selected.length < 2} loading={preview.isPending} onClick={() => preview.mutate(request)}>预览兼容性</Button></Space>
    </Card>
    {preview.data && <Card title="3. 兼容性预览" extra={<Tag color={preview.data.status === 'not_directly_comparable' ? 'orange' : 'green'}>{preview.data.status}</Tag>}>
      <Alert type={preview.data.status === 'not_directly_comparable' ? 'warning' : 'success'} showIcon title={preview.data.message_zh} description="请确认后才会创建 Comparison；预览不会修改运行记录。" />
      <Table rowKey="name" pagination={false} style={{ marginTop: 16 }} dataSource={preview.data.dimensions} columns={[{ title: '维度', dataIndex: 'name' }, { title: '是否一致', dataIndex: 'equal', render: (v: boolean) => v ? '是' : '否' }, { title: '默认冻结', dataIndex: 'frozen_by_default', render: (v: boolean) => v ? '是' : '否' }, { title: '差异已声明', dataIndex: 'declared_varying', render: (v: boolean) => v ? '是' : '否' }]} />
      <Space style={{ marginTop: 16 }}><Button type="primary" loading={create.isPending} onClick={() => create.mutate({ ...request, confirmed: true })}>确认创建 Comparison</Button><Text type="secondary">当前选择：{selectedRuns.length} 条运行记录</Text></Space>
    </Card>}
    {create.data && <Alert type="success" showIcon title="Comparison 已创建" description={<Link to={`/comparisons/${create.data.comparison_id}`}>{create.data.comparison_id}（待独立验证）</Link>} />}
  </Space>;
}
