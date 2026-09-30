import {
  AuditOutlined,
  ClusterOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  RadarChartOutlined,
} from '@ant-design/icons';
import { Alert, Badge, Layout, Menu, Space, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import { useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useBackends } from '../api/backends';
import { useHealth } from '../api/health';
import { useSystemBackends } from '../api/system';

const { Header, Sider, Content, Footer } = Layout;

function navLabel(zh: string, en: string) {
  return (
    <span className="nav-label">
      <span className="nav-label__zh">{zh}</span>
      <span className="nav-label__en">{en}</span>
    </span>
  );
}

const NAV_ITEMS: NonNullable<MenuProps['items']> = [
  { key: '/overview', icon: <DashboardOutlined />, label: navLabel('平台概览', 'Overview') },
  { key: 'group-scenarios', icon: <EnvironmentOutlined />, label: navLabel('场景', 'Scenarios'), children: [
    { key: '/scenarios', label: '已配置场景库' }, { key: '/scenarios/advanced', label: '候选组合 / 高级视图' },
    { key: '/scenarios/assets/antenna', label: '环境资产 / 天线' }, { key: '/scenarios/ue', label: 'UE Twin 几何' },
    { key: '/scenarios/radio', label: '无线观测示例' }, { key: '/scenarios/association', label: '用户关联' },
  ] },
  { key: 'group-experiments', icon: <ExperimentOutlined />, label: navLabel('实验', 'Experiments'), children: [
    { key: '/experiments', label: '实验记录' }, { key: '/system', label: '系统级仿真' }, { key: '/optimizations', label: '优化运行' },
  ] },
  { key: 'group-algorithms', icon: <NodeIndexOutlined />, label: navLabel('算法', 'Algorithms'), children: [
    { key: '/algorithms', label: '算法目录' }, { key: '/algorithm-onboarding', label: '算法接入' },
  ] },
  { key: 'group-analysis', icon: <RadarChartOutlined />, label: navLabel('分析', 'Analysis'), children: [
    { key: '/benchmarks', label: '算法 Benchmark' }, { key: '/comparisons', label: '运行对比' },
  ] },
  { key: '/acceptance', icon: <AuditOutlined />, label: navLabel('验收', 'Acceptance') },
  { key: 'group-system', icon: <ClusterOutlined />, label: navLabel('系统', 'System'), children: [
    { key: '/platform-status', label: '平台能力状态' },
  ] },
];

function selectedNavKey(pathname: string): string {
  const keys = ['/scenarios/assets/antenna', '/scenarios/advanced', '/scenarios/association', '/scenarios/radio', '/scenarios/ue', '/algorithm-onboarding', '/optimizations', '/experiments', '/benchmarks', '/comparisons', '/algorithms', '/acceptance', '/platform-status', '/system', '/scenarios', '/overview'];
  const match = keys.find((k) =>
    pathname.startsWith(k),
  );
  return match ?? '/overview';
}

/** Header 右侧后端状态，全部来自 GET /api/v1/backends。 */
function BackendStatus() {
  const { data, isLoading, isError } = useBackends();
  const system = useSystemBackends();
  if (isLoading) return <Badge status="processing" text="检查后端… Checking backend" />;
  if (isError || !data) return <Badge status="error" text="API 不可达 / API unreachable" />;
  const all = [...data, ...(system.data ?? [])];
  if (all.length === 0) return <Badge status="warning" text="无仿真后端 / No backend" />;
  return (
    <Space size="large">
      {all.map((b) => (
        <Tooltip
          key={b.id}
          title={b.available ? `${b.name_en}${b.version ? ` · v${b.version}` : ''}` : b.reason ?? b.name_en}
        >
          <Badge
            status={b.available ? 'success' : 'error'}
            text={
              <span className="backend-status">
                {b.name_zh}
                <span className="backend-status__state">{b.available ? '就绪 Ready' : '不可用 Unavailable'}</span>
              </span>
            }
          />
        </Tooltip>
      ))}
    </Space>
  );
}

export function PlatformLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: health } = useHealth();
  const activeGroup = location.pathname.startsWith('/scenarios') ? 'group-scenarios'
    : ['/experiments', '/system', '/optimizations'].some((path) => location.pathname.startsWith(path)) ? 'group-experiments'
      : ['/algorithms', '/algorithm-onboarding'].some((path) => location.pathname.startsWith(path)) ? 'group-algorithms'
        : ['/benchmarks', '/comparisons'].some((path) => location.pathname.startsWith(path)) ? 'group-analysis'
          : location.pathname.startsWith('/platform-status') ? 'group-system' : '';
  const [openKeys, setOpenKeys] = useState<string[]>(activeGroup ? [activeGroup] : []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  useEffect(() => { setOpenKeys(activeGroup ? [activeGroup] : []); }, [activeGroup]);

  return (
    <Layout className="platform">
      <Header className="platform__header">
        <div className="brand" onClick={() => navigate('/overview')} role="link" tabIndex={0}>
          <div className="brand__logo">5G</div>
          <div className="brand__text">
            <div className="brand__zh">5G网络学习优化仿真验证平台</div>
            <div className="brand__en">5G Learning Optimization Simulation &amp; Validation Platform</div>
          </div>
        </div>
        <BackendStatus />
      </Header>
      {health?.testing && (
        <Alert
          type="warning"
          banner
          showIcon
          title="开发测试模式 / Development Test Mode — 后端以 TESTING=true 启动，可能包含 FakeBackend 测试夹具数据（TEST FIXTURE）。"
        />
      )}
      <Layout>
        <Sider width={256} theme="light" className="platform__sider">
          <Menu
            mode="inline"
            openKeys={openKeys}
            selectedKeys={[selectedNavKey(location.pathname)]}
            items={NAV_ITEMS}
            onOpenChange={(keys) => setOpenKeys(keys.length ? [String(keys[keys.length - 1])] : [])}
            onClick={({ key }) => { if (String(key).startsWith('/')) navigate(key); }}
          />
        </Sider>
        <Layout className="platform__main">
          <Content className="platform__content">
            <Outlet />
          </Content>
          <Footer className="platform__footer">
            V0.3{health ? ` · API v${health.version}` : ''} · Data Source: Simulation Generated · 数据来源：仿真生成
          </Footer>
        </Layout>
      </Layout>
    </Layout>
  );
}
