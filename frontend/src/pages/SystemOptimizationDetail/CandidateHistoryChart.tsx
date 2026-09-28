import { ScatterChart } from 'echarts/charts';
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useMemo, useRef } from 'react';

import type { SystemOptimizationCandidate } from '../../types/systemOptimization';
import { formatMbps, formatParameter } from '../../utils/systemOptimization';

echarts.use([ScatterChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  candidates: SystemOptimizationCandidate[];
  baseline: SystemOptimizationCandidate | null;
  bestCandidateId: string | null;
  parameterId: string;
  height?: number;
}

/**
 * 候选评价历史：横轴参数值、纵轴目标值（网络吞吐率），每个点都是一次真实评估。
 * Grid Search 是穷举而非迭代收敛，因此只画离散点，不画平滑曲线。
 */
export function CandidateHistoryChart({ candidates, baseline, bestCandidateId, parameterId, height = 300 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const rows = useMemo(
    () => candidates.filter((c) => c.status === 'evaluated' && c.objective).sort((a, b) => a.iteration - b.iteration),
    [candidates],
  );

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    const point = (c: SystemOptimizationCandidate) => ({
      value: [c.parameters[parameterId], c.objective?.value ?? null],
      candidate: c,
    });
    const best = rows.filter((c) => c.candidate_id === bestCandidateId);
    const others = rows.filter((c) => c.candidate_id !== bestCandidateId);
    const baselineValue = baseline?.objective?.value;
    chart.setOption({
      grid: { left: 64, right: 32, top: 40, bottom: 48 },
      legend: { top: 0, data: ['Candidate', 'Best'] },
      tooltip: {
        trigger: 'item',
        formatter: (p: { data: { candidate: SystemOptimizationCandidate } }) => {
          const c = p.data.candidate;
          return [
            `<b>${c.candidate_id}</b>${c.candidate_id === bestCandidateId ? ' · BEST' : ''}${c.reused_baseline ? ' · Reused Baseline' : ''}`,
            `${parameterId}: ${formatParameter(c.parameters[parameterId])}`,
            `Network: ${formatMbps(c.network_throughput_mbps?.mean)}`,
            `Average: ${formatMbps(c.average_ue_throughput_mbps?.mean)}`,
            `P5: ${formatMbps(c.p5_ue_throughput_mbps?.mean)}`,
          ].join('<br/>');
        },
      },
      xAxis: { type: 'value', name: parameterId, nameLocation: 'middle', nameGap: 30, scale: true },
      yAxis: { type: 'value', name: 'Network Throughput (Mbps)', scale: true },
      series: [
        {
          name: 'Candidate',
          type: 'scatter',
          symbolSize: 12,
          itemStyle: { color: '#1d4ed8' },
          data: others.map(point),
          markLine:
            typeof baselineValue === 'number'
              ? {
                  symbol: 'none',
                  lineStyle: { type: 'dashed', color: '#f59e0b' },
                  label: { formatter: 'Baseline', position: 'end', color: '#b45309' },
                  data: [{ yAxis: baselineValue }],
                }
              : undefined,
        },
        { name: 'Best', type: 'scatter', symbol: 'diamond', symbolSize: 18, itemStyle: { color: '#16a34a' }, data: best.map(point) },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [rows, baseline, bestCandidateId, parameterId]);

  return <div ref={ref} style={{ width: '100%', height }} role="img" aria-label="Candidate history chart" />;
}
