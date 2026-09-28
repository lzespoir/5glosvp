import { LineChart } from 'echarts/charts';
import {
  GridComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useMemo, useRef } from 'react';

import type { OptimizationCandidate } from '../../types/optimization';
import { formatPercent } from '../../utils/format';
import { candidatePower, component, formatObjective, formatPower } from '../../utils/optimization';

echarts.use([LineChart, GridComponent, MarkLineComponent, MarkPointComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  candidates: OptimizationCandidate[];
  baseline: OptimizationCandidate | null;
  bestCandidateId: string | null;
  height?: number;
}

/**
 * 候选评价历史：每个点都是后端真实评价过的候选。
 * 网格搜索是穷举评价而非迭代收敛，因此不画平滑曲线，也不称为"收敛曲线"。
 */
export function ObjectiveHistoryChart({ candidates, baseline, bestCandidateId, height = 300 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const rows = useMemo(() => candidates.slice().sort((a, b) => a.iteration - b.iteration), [candidates]);

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    const bestIndex = rows.findIndex((c) => c.candidate_id === bestCandidateId);
    const best = bestIndex >= 0 ? rows[bestIndex] : undefined;
    const baselineValue = baseline?.objective?.value;

    chart.setOption({
      grid: { left: 64, right: 72, top: 32, bottom: 56 },
      tooltip: {
        trigger: 'item',
        formatter: (p: { dataIndex: number }) => {
          const c = rows[p.dataIndex];
          if (!c) return '';
          const lines = [
            `<b>${c.candidate_id}</b>${c.candidate_id === bestCandidateId ? ' · BEST' : ''}${c.reused_baseline ? ' · Reused Baseline' : ''}`,
            `TX Power: ${formatPower(candidatePower(c))}`,
            `Objective J: ${formatObjective(c.objective?.value)}`,
            `SINR Coverage: ${formatPercent(component(c, 'sinr_coverage_ratio'), 2)}`,
            `Power Cost c_P: ${formatObjective(component(c, 'normalized_power_cost'), 3)}`,
          ];
          return lines.join('<br/>');
        },
      },
      xAxis: {
        type: 'category',
        name: 'Candidate',
        nameLocation: 'middle',
        nameGap: 40,
        data: rows.map((c) => `${c.candidate_id}\n${formatPower(candidatePower(c))}`),
        axisLabel: { fontSize: 10 },
      },
      yAxis: { type: 'value', name: 'Objective J', scale: true },
      series: [
        {
          name: 'Objective',
          type: 'line',
          smooth: false,
          symbol: 'circle',
          symbolSize: 9,
          lineStyle: { width: 1, type: 'dotted', color: '#94a3b8' },
          itemStyle: { color: '#1d4ed8' },
          data: rows.map((c) => (c.status === 'evaluated' ? (c.objective?.value ?? null) : null)),
          markPoint: best?.objective
            ? {
                symbol: 'pin',
                symbolSize: 46,
                itemStyle: { color: '#16a34a' },
                label: { formatter: 'BEST', fontSize: 10, color: '#fff' },
                data: [{ coord: [bestIndex, best.objective.value] }],
              }
            : undefined,
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
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [rows, baseline, bestCandidateId]);

  return <div ref={ref} style={{ width: '100%', height }} role="img" aria-label="Candidate objective history chart" />;
}
