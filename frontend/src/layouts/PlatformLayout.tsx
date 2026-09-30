import {
  AuditOutlined,
  ClusterOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
  ExperimentOutlined,
  FunctionOutlined,
  NodeIndexOutlined,
  RadarChartOutlined,
} from '@ant-design/icons';
import { Alert, Badge, Layout, Menu, Space, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import { useEffect } from 'react';
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
  { key: '/scenarios', icon: <EnvironmentOutlined />, label: navLabel('场景中心', 'Scenario Center') },
  { key: '/a-matrix', icon: <RadarChartOutlined />, label: navLabel('A矩阵 / UE Twin', 'A-Matrix / UE Twin') },
  { key: '/user-association', icon: <ClusterOutlined />, label: navLabel('用户关联', 'User Association') },
  { key: '/benchmarks', icon: <FunctionOutlined />, label: navLabel('算法对比', 'Benchmark') },
  { key: '/system', icon: <ClusterOutlined />, label: navLabel('系统级仿真', 'System Simulation') },
  { key: '/optimizations', icon: <FunctionOutlined />, label: navLabel('优化中心', 'Optimization Center') },
  { key: '/algorithms', icon: <NodeIndexOutlined />, label: navLabel('算法中心', 'Algorithm Center') },
  { key: '/experiments', icon: <ExperimentOutlined />, label: navLabel('实验中心', 'Experiment Center') },
  { key: '/acceptance', icon: <AuditOutlined />, label: navLabel('验收中心', 'Acceptance Center') },
];

function selectedNavKey(pathname: string): string {
  const keys = ['/overview', '/scenarios', '/a-matrix', '/user-association', '/benchmarks', '/system', '/optimizations', '/algorithms', '/experiments', '/acceptance'];
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

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

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
        <Sider width={208} theme="light" className="platform__sider">
          <Menu
            mode="inline"
            selectedKeys={[selectedNavKey(location.pathname)]}
            items={NAV_ITEMS}
            onClick={({ key }) => navigate(key)}
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
