import { LineChart, ScatterChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useRef } from 'react';

import type { AlgorithmTrace, TraceEvaluation } from '../../types/algorithm';
import { formatParameter } from '../../utils/systemOptimization';

echarts.use([LineChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  trace: AlgorithmTrace;
  parameterId: string;
  height?: number;
}

/**
 * 算法轨迹：横轴为评价顺序（0 = 基线），纵轴为目标值。
 * 点 = 真实评价；阶梯线 = 平台规则下的 best-so-far（记录值，不是拟合 / 平滑曲线）。
 */
export function AlgorithmTraceChart({ trace, parameterId, height = 300 }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    const rows = trace.evaluations;
    const point = (e: TraceEvaluation) => ({ value: [e.sequence, e.objective], e });
    chart.setOption({
      grid: { left: 64, right: 32, top: 40, bottom: 48 },
      legend: { top: 0, data: ['Evaluation', 'Best so far'] },
      tooltip: {
        trigger: 'item',
        formatter: (p: { data: { e: TraceEvaluation } }) => {
          const e = p.data.e;
          return [
            `<b>#${e.sequence} ${e.candidate_id}</b> · round ${e.round}${e.cache_hit ? ' · cache hit' : ''}`,
            `${parameterId}: ${formatParameter(e.parameters[parameterId])}`,
            `Objective: ${e.objective === null ? '—' : e.objective.toFixed(4)}`,
            `Best so far: ${e.best_so_far_candidate_id ?? '—'}`,
          ].join('<br/>');
        },
      },
      xAxis: { type: 'value', name: 'Evaluation #', nameLocation: 'middle', nameGap: 30, minInterval: 1 },
      yAxis: { type: 'value', name: 'Objective (Mbps)', scale: true },
      series: [
        {
          name: 'Evaluation',
          type: 'scatter',
          symbolSize: 11,
          itemStyle: { color: '#1d4ed8' },
          data: rows.filter((e) => e.objective !== null).map(point),
        },
        {
          name: 'Best so far',
          type: 'line',
          step: 'end',
          symbol: 'none',
          lineStyle: { color: '#16a34a', width: 2 },
          data: rows
            .filter((e) => e.best_so_far_objective !== null)
            .map((e) => ({ value: [e.sequence, e.best_so_far_objective], e })),
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [trace, parameterId]);

  return <div ref={ref} style={{ width: '100%', height }} role="img" aria-label="Algorithm trace chart" />;
}
