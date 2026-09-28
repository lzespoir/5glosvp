import { ScatterChart } from 'echarts/charts';
import { GridComponent, MarkAreaComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useRef } from 'react';

import { formatValue, trimNumber } from '../../utils/format';

echarts.use([ScatterChart, GridComponent, MarkAreaComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

export interface NetworkNode {
  id: string;
  position: number[];
  /** UE 吞吐率（后端 KPI 结果）；null 表示不可用 */
  throughputMbps?: number | null;
}

interface Props {
  baseStations: NetworkNode[];
  ues: NetworkNode[];
  /** UE 生成区域（场景尚未运行时显示）*/
  area?: { center: number[]; size: number[] } | null;
  height?: number;
  onSelectUe?: (ueId: string) => void;
}

/** 二维网络视图：BS ▲、UE ●，坐标为场景坐标 [m]，不绘制任何地图底图。 */
export function NetworkView({ baseStations, ues, area, height = 360, onSelectUe }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    const throughputs = ues.map((u) => u.throughputMbps).filter((v): v is number => typeof v === 'number');
    const hasThroughput = throughputs.length > 0;
    const [cx, cy] = area?.center ?? [];
    const [sx, sy] = area?.size ?? [];
    const areaBox =
      cx !== undefined && cy !== undefined && sx !== undefined && sy !== undefined
        ? [
            [cx - sx / 2, cy - sy / 2],
            [cx + sx / 2, cy + sy / 2],
          ]
        : null;
    chart.setOption({
      grid: { left: 64, right: hasThroughput ? 96 : 24, top: 24, bottom: 48 },
      tooltip: {
        trigger: 'item',
        formatter: (p: { seriesName: string; data: { name: string; value: number[]; tput?: number | null } }) => {
          const d = p.data;
          const pos = `(${trimNumber(d.value[0] ?? NaN, 1)}, ${trimNumber(d.value[1] ?? NaN, 1)}) m`;
          if (p.seriesName === 'BS') return `<b>${d.name}</b> 基站 BS<br/>${pos}`;
          const tput = d.tput === undefined ? '' : `<br/>吞吐率 Throughput: ${formatValue(d.tput, 'Mbps', 2)}`;
          return `<b>${d.name}</b><br/>${pos}${tput}`;
        },
      },
      xAxis: { type: 'value', name: 'x [m]', nameLocation: 'middle', nameGap: 28, scale: true },
      yAxis: { type: 'value', name: 'y [m]', nameLocation: 'middle', nameGap: 44, scale: true },
      visualMap: hasThroughput
        ? {
            type: 'continuous',
            seriesIndex: 1,
            dimension: 2,
            min: Math.min(...throughputs),
            max: Math.max(...throughputs),
            right: 8,
            top: 'middle',
            text: ['Mbps', ''],
            calculable: false,
            inRange: { color: ['#fde68a', '#16a34a', '#1d4ed8'] },
          }
        : undefined,
      series: [
        {
          name: 'BS',
          type: 'scatter',
          symbol: 'triangle',
          symbolSize: 22,
          itemStyle: { color: '#dc2626' },
          label: { show: true, formatter: '{b}', position: 'top', fontSize: 11 },
          data: baseStations.map((b) => ({ name: b.id, value: [b.position[0], b.position[1]] })),
          markArea: areaBox
            ? {
                silent: true,
                itemStyle: { color: 'rgba(29, 78, 216, 0.06)', borderColor: '#93c5fd', borderType: 'dashed', borderWidth: 1 },
                label: { show: true, position: 'insideTopLeft', formatter: 'UE 生成区域 UE area', color: '#1d4ed8' },
                data: [[{ coord: areaBox[0] }, { coord: areaBox[1] }]],
              }
            : undefined,
        },
        {
          name: 'UE',
          type: 'scatter',
          symbol: 'circle',
          symbolSize: 14,
          itemStyle: { color: '#1d4ed8', borderColor: '#0f172a', borderWidth: 1 },
          label: { show: true, formatter: '{b}', position: 'right', fontSize: 10 },
          data: ues.map((u) => ({
            name: u.id,
            value: [u.position[0], u.position[1], u.throughputMbps ?? null],
            tput: u.throughputMbps,
          })),
        },
      ],
    });
    if (onSelectUe) {
      chart.on('click', (p) => {
        if (p.seriesName === 'UE' && typeof p.name === 'string') onSelectUe(p.name);
      });
    }
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [baseStations, ues, area, onSelectUe]);

  return <div ref={ref} style={{ width: '100%', height }} role="img" aria-label="Network view: base stations and UEs" />;
}
