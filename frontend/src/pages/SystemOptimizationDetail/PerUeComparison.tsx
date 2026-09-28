import { BarChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { Table, Tag } from 'antd';
import { useEffect, useMemo, useRef } from 'react';

import type { SystemOptimizationCandidate } from '../../types/systemOptimization';
import { formatMbps } from '../../utils/systemOptimization';

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  baseline: SystemOptimizationCandidate;
  best: SystemOptimizationCandidate;
}

interface Row {
  ue_id: string;
  baseline: number;
  best: number;
}

/** 每个 UE 的基线 / 最优吞吐率（后端给出的 per_ue_throughput_mbps）；下降的 UE 明确标出。 */
export function PerUeComparison({ baseline, best }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const rows = useMemo<Row[]>(
    () =>
      Object.entries(baseline.per_ue_throughput_mbps).map(([ue, value]) => ({
        ue_id: ue,
        baseline: value,
        best: best.per_ue_throughput_mbps[ue] ?? Number.NaN,
      })),
    [baseline, best],
  );

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 56, right: 16, top: 36, bottom: 32 },
      legend: { top: 0 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: rows.map((r) => r.ue_id) },
      yAxis: { type: 'value', name: 'Mbps' },
      series: [
        { name: `Baseline (${baseline.candidate_id})`, type: 'bar', itemStyle: { color: '#f59e0b' }, data: rows.map((r) => r.baseline) },
        { name: `Best (${best.candidate_id})`, type: 'bar', itemStyle: { color: '#16a34a' }, data: rows.map((r) => r.best) },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [rows, baseline.candidate_id, best.candidate_id]);

  return (
    <>
      <div ref={ref} style={{ width: '100%', height: 260 }} role="img" aria-label="Per-UE throughput comparison chart" />
      <Table<Row>
        rowKey="ue_id"
        size="small"
        pagination={false}
        dataSource={rows}
        data-testid="per-ue-table"
        columns={[
          { title: 'UE', dataIndex: 'ue_id', render: (v: string) => <code>{v}</code> },
          { title: '基线 Baseline', dataIndex: 'baseline', align: 'right', render: (v: number) => formatMbps(v, 3) },
          { title: '最优 Best', dataIndex: 'best', align: 'right', render: (v: number) => formatMbps(v, 3) },
          {
            title: '变化 Change',
            key: 'change',
            align: 'right',
            render: (_, r) =>
              r.best < r.baseline ? (
                <Tag color="error">↓ decrease</Tag>
              ) : r.best > r.baseline ? (
                <Tag color="success">↑ increase</Tag>
              ) : (
                <Tag>→ unchanged</Tag>
              ),
          },
        ]}
      />
    </>
  );
}
