import { BarChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useMemo, useRef } from 'react';

import type { ExperimentResponse } from '../../types/experiment';
import { isNumber } from '../../utils/format';

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  experiments: ExperimentResponse[];
  height?: number;
}

/** 最近实验运行耗时：只使用 API 返回的真实实验，按时间从旧到新排列。 */
export function RuntimeChart({ experiments, height = 260 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const rows = useMemo(
    () => experiments.filter((e) => isNumber(e.runtime.total_seconds)).slice().reverse(),
    [experiments],
  );

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 56, right: 16, top: 36, bottom: 56 },
      tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => `${Number(v).toFixed(3)} s` },
      legend: { data: ['Total', 'Simulation'], top: 0, right: 0, textStyle: { fontSize: 11 } },
      xAxis: {
        type: 'category',
        name: 'Experiment',
        nameLocation: 'middle',
        nameGap: 40,
        data: rows.map((e) => e.experiment_id.replace('EXP-', '')),
        axisLabel: { fontSize: 10, rotate: 30 },
      },
      yAxis: { type: 'value', name: 'Runtime (s)' },
      series: [
        {
          name: 'Total',
          type: 'bar',
          data: rows.map((e) => e.runtime.total_seconds),
          itemStyle: { color: '#93c5fd' },
        },
        {
          name: 'Simulation',
          type: 'bar',
          barGap: '-100%',
          data: rows.map((e) => e.runtime.simulation_seconds ?? null),
          itemStyle: { color: '#1d4ed8' },
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [rows]);

  return <div ref={ref} style={{ width: '100%', height }} role="img" aria-label="Recent experiment runtime chart" />;
}
