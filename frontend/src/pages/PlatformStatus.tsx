import { useEffect, useState } from 'react';
import { Alert, Card, Table, Tag } from 'antd';
import { workspaceApi, type Capability } from '../api/workspace';
import { PageHeader } from '../components/PageHeader';

export function PlatformStatusPage() {
  const [items, setItems] = useState<Capability[]>([]);
  const [error, setError] = useState('');
  useEffect(() => { workspaceApi.capabilities().then(setItems).catch((cause) => setError(String(cause))); }, []);
  return <><PageHeader titleZh="平台能力状态" titleEn="Capability Registry" subtitle="能力声明由后端注册表返回；实现、验证与验收证据分别标注。" />{error && <Alert type="error" title="能力状态加载失败" description={error} />}<Card><Table rowKey="capability_id" dataSource={items} pagination={false} columns={[{ title: '能力', dataIndex: 'name' }, { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color={value === 'VERIFIED' ? 'green' : value === 'IMPLEMENTED' ? 'blue' : 'default'}>{value}</Tag> }, { title: '版本', dataIndex: 'implementation_version' }, { title: '证据指针', dataIndex: 'evidence_refs', render: (value: string[]) => value.join(', ') || '—' }, { title: '限制', dataIndex: 'limitations', render: (value: string[]) => value.join('；') || '—' }]} /></Card></>;
}
