import { Button, Card, Empty, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useExperiments } from '../../api/experiments';
import { ErrorState } from '../../components/ErrorState';
import { PageHeader } from '../../components/PageHeader';
import { StatusTag } from '../../components/StatusTag';
import type { ExperimentResponse } from '../../types/experiment';
import { formatDateTime, formatSeconds } from '../../utils/format';

export const PAGE_SIZE = 20;

const columns: ColumnsType<ExperimentResponse> = [
  { title: '实验编号 Experiment ID', dataIndex: 'experiment_id', render: (id: string) => <code>{id}</code> },
  {
    title: '场景 Scenario',
    key: 'scenario',
    render: (_, e) => (
      <>
        {e.scenario.name_zh}
        <div className="muted">{e.scenario.scenario_id}</div>
      </>
    ),
  },
  {
    title: '后端 Backend',
    key: 'backend',
    render: (_, e) => `${e.backend.id}${e.backend.version ? ` ${e.backend.version}` : ''}`,
  },
  { title: '状态 Status', dataIndex: 'status', render: (_, e) => <StatusTag status={e.status} /> },
  { title: '仿真耗时 Simulation', key: 'sim', align: 'right', render: (_, e) => formatSeconds(e.runtime.simulation_seconds) },
  { title: '总耗时 Total', key: 'total', align: 'right', render: (_, e) => formatSeconds(e.runtime.total_seconds) },
  { title: '创建时间 Created', dataIndex: 'created_at', render: (v: string) => formatDateTime(v) },
];

export function ExperimentsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const query = useExperiments(PAGE_SIZE, (page - 1) * PAGE_SIZE);
  const data = query.data;

  return (
    <>
      <PageHeader
        titleZh="实验中心"
        titleEn="Experiment Center"
        subtitle="全部仿真实验记录 · All simulation experiments"
        extra={<Button type="primary" onClick={() => navigate('/scenarios')}>新建实验 New Experiment</Button>}
      />
      <Card>
        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : (
          <Table
            rowKey="experiment_id"
            size="middle"
            columns={columns}
            dataSource={data?.items ?? []}
            loading={query.isLoading || query.isFetching}
            rowClassName="clickable-row"
            onRow={(e) => ({ onClick: () => navigate(`/experiments/${e.experiment_id}`) })}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: data?.total ?? 0,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 个实验 / ${total} experiments`,
              onChange: setPage,
            }}
            locale={{
              emptyText: (
                <Empty
                  description={
                    <>
                      <div className="empty-title">暂无实验 / No experiments yet</div>
                      <div className="muted">选择一个仿真场景，开始第一次 Sionna RT 实验。</div>
                    </>
                  }
                >
                  <Button type="primary" onClick={() => navigate('/scenarios')}>前往场景中心</Button>
                </Empty>
              ),
            }}
          />
        )}
      </Card>
    </>
  );
}
