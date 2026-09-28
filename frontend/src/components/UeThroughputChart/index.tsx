import { BarChart } from 'echarts/charts';
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useMemo, useRef } from 'react';

import type { UserEquipmentResult } from '../../types/system';
import { formatValue } from '../../utils/format';

echarts.use([BarChart, GridComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  ues: UserEquipmentResult[];
  /** 平均与 P5 均为后端 KPI 引擎结果，前端只画参考线不计算 */
  averageMbps: number | null;
  p5Mbps: number | null;
  height?: number;
}

/** UE 吞吐率分布（按吞吐率升序）。吞吐率不可用的 UE 显示为空柱而非 0。 */
export function UeThroughputChart({ ues, averageMbps, p5Mbps, height = 320 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const rows = useMemo(
    () => ues.slice().sort((a, b) => (a.throughput_mbps ?? -Infinity) - (b.throughput_mbps ?? -Infinity)),
    [ues],
  );

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    const lines: { yAxis: number; name: string; lineStyle: { color: string; type: string } }[] = [];
    if (typeof averageMbps === 'number') {
      lines.push({ yAxis: averageMbps, name: 'Avg', lineStyle: { color: '#16a34a', type: 'dashed' } });
    }
    if (typeof p5Mbps === 'number') {
      lines.push({ yAxis: p5Mbps, name: 'P5', lineStyle: { color: '#f59e0b', type: 'dashed' } });
    }
    chart.setOption({
      grid: { left: 64, right: 56, top: 28, bottom: 40 },
      tooltip: {
        trigger: 'item',
        formatter: (p: { dataIndex: number }) => {
          const u = rows[p.dataIndex];
          return u ? `<b>${u.ue_id}</b><br/>UE Throughput: ${formatValue(u.throughput_mbps, 'Mbps', 2)}` : '';
        },
      },
      xAxis: { type: 'category', data: rows.map((u) => u.ue_id), axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', name: 'Mbps' },
      series: [
        {
          name: 'UE Throughput',
          type: 'bar',
          barMaxWidth: 42,
          itemStyle: { color: '#1d4ed8' },
          data: rows.map((u) => u.throughput_mbps),
          markLine: lines.length
            ? {
                symbol: 'none',
                label: { formatter: (p: { name: string; value: number }) => `${p.name} ${p.value.toFixed(1)}`, position: 'end' },
                data: lines,
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
  }, [rows, averageMbps, p5Mbps]);

  return <div ref={ref} style={{ width: '100%', height }} role="img" aria-label="UE throughput distribution chart" />;
}
