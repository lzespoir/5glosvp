import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Select, Slider, Space, Spin, Tag, Typography } from 'antd';
import { apiClient } from '../../api/client';
import type { AMatrixPattern } from '../../types/day13';

interface Profile { profile_id: string; name: string; library: string; beam_type: string; beam_ids: number[]; artifact_hash: string }
interface PatternEntry { beam: number; pattern: AMatrixPattern }
const COLORS = ['#1677ff', '#fa8c16', '#52c41a', '#eb2f96', '#722ed1', '#13c2c2', '#fa541c', '#2f54eb'];

function PatternCanvas({ entries, mode, yaw, pitch, stride }: { entries: PatternEntry[]; mode: '3d' | '2d'; yaw: number; pitch: number; stride: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current; const ctx = canvas?.getContext('2d'); if (!canvas || !ctx) return;
    const width = canvas.width; const height = canvas.height;
    ctx.clearRect(0, 0, width, height); ctx.fillStyle = '#f7faff'; ctx.fillRect(0, 0, width, height);
    if (!entries.length) return;
    if (mode === '2d') {
      const grid = entries[0]?.pattern.normalized_response ?? [];
      grid.forEach((row, r) => row.forEach((raw, c) => { const value = Math.max(0, Math.min(1, raw)); ctx.fillStyle = `hsl(${230 - value * 220} 90% 48%)`; ctx.fillRect(c * width / 72, r * height / 91, width / 72 + 0.4, height / 91 + 0.4); }));
      return;
    }
    const yawR = yaw * Math.PI / 180; const pitchR = pitch * Math.PI / 180;
    const project = (el: number, az: number, response: number) => {
      const elevation = el * Math.PI / 180; const azimuth = az * Math.PI / 180;
      const radius = 0.18 + Math.max(0, Math.min(1, response)) * 0.82;
      const x = radius * Math.cos(elevation) * Math.cos(azimuth);
      const y = radius * Math.cos(elevation) * Math.sin(azimuth);
      const z = radius * Math.sin(elevation);
      const xr = x * Math.cos(yawR) - y * Math.sin(yawR);
      const yr = x * Math.sin(yawR) + y * Math.cos(yawR);
      return { x: width / 2 + xr * 175, y: height / 2 - (z * Math.cos(pitchR) - yr * Math.sin(pitchR)) * 175, depth: z * Math.sin(pitchR) + yr * Math.cos(pitchR) };
    };
    ctx.strokeStyle = '#d2dce8'; ctx.lineWidth = 1;
    for (const el of [-60, -30, 0, 30, 60]) { ctx.beginPath(); for (let az = 0; az <= 360; az += 5) { const p = project(el, az, 1); if (az === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y); } ctx.stroke(); }
    const dots: { x: number; y: number; depth: number; color: string }[] = [];
    entries.forEach(({ pattern }, index) => pattern.normalized_response.forEach((row, r) => {
      if (r % stride !== 0) return;
      row.forEach((value, c) => { if (c % stride !== 0) return; const p = project(-90 + r * 2, c * 5, value); dots.push({ ...p, color: COLORS[index % COLORS.length] ?? '#1677ff' }); });
    }));
    dots.sort((a, b) => a.depth - b.depth);
    dots.forEach((point) => { ctx.fillStyle = point.color; ctx.globalAlpha = 0.55 + (point.depth + 1) * 0.14; ctx.fillRect(point.x, point.y, 2.6, 2.6); }); ctx.globalAlpha = 1;
    ctx.fillStyle = '#536b86'; ctx.font = '12px sans-serif'; ctx.fillText('relative response, peak = 1 · 3D spherical projection', 12, height - 12);
  }, [entries, mode, yaw, pitch, stride]);
  return <canvas ref={ref} width={760} height={420} style={{ width: '100%', maxWidth: 760, border: '1px solid #dce4ee', borderRadius: 8 }} aria-label={mode === '3d' ? 'A-Matrix relative spherical beam pattern' : 'A-Matrix relative angular heatmap'} />;
}

export function AntennaPatternViewer() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profileId, setProfileId] = useState('');
  const [beamIndex, setBeamIndex] = useState(0);
  const [overlay, setOverlay] = useState<1 | 4 | 8>(1);
  const [mode, setMode] = useState<'3d' | '2d'>('3d');
  const [yaw, setYaw] = useState(35);
  const [pitch, setPitch] = useState(22);
  const [stride, setStride] = useState(3);
  const [entries, setEntries] = useState<PatternEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { apiClient.get<{ items: Profile[] }>('/workspace/antennas/a-matrix/options').then(({ data }) => { setProfiles(data.items); setProfileId((current) => current || data.items[0]?.profile_id || ''); }).catch((cause) => setError(String(cause))); }, []);
  const profile = profiles.find((item) => item.profile_id === profileId);
  const ids = profile?.beam_ids ?? [];
  useEffect(() => { setBeamIndex(0); }, [profileId]);
  useEffect(() => {
    if (!profile) return;
    let cancelled = false; setBusy(true); setError('');
    apiClient.get<{ items: { id: string; library: string; beam_type: string; keys_by_beam: Record<string, string> }[] }>('/a-matrix/profiles').then(async ({ data }) => {
      const raw = data.items.find((item) => item.id === profile.profile_id);
      if (!raw) throw new Error('A-Matrix profile not found');
      const selected = Array.from({ length: Math.min(overlay, ids.length) }, (_, index) => ids[(beamIndex + index) % ids.length]).filter((beam): beam is number => beam !== undefined);
      const result = await Promise.all(selected.map(async (beam) => ({ beam, pattern: (await apiClient.get<AMatrixPattern>('/a-matrix/pattern', { params: { library: raw.library, beam_type: raw.beam_type, entry_key: raw.keys_by_beam[String(beam)] } })).data })));
      if (!cancelled) setEntries(result);
    }).catch((cause) => { if (!cancelled) setError(String(cause)); }).finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [profileId, beamIndex, overlay, profiles]);
  const nextBeam = (step: number) => setBeamIndex((current) => Math.max(0, Math.min(ids.length - 1, current + step)));
  return <Card title="球面方向图 · 相对 A-Matrix 响应" tabIndex={0} onKeyDown={(event) => { if (event.key === 'ArrowUp') nextBeam(-1); if (event.key === 'ArrowDown') nextBeam(1); }}>
    <Space wrap className="section-bottom"><Select aria-label="A-Matrix profile" value={profileId || undefined} onChange={setProfileId} style={{ minWidth: 260 }} options={profiles.map((item) => ({ value: item.profile_id, label: `${item.name} · ${item.library}` }))} /><Select aria-label="显示模式" value={mode} onChange={setMode} options={[{ value: '3d', label: '3D 球面（默认）' }, { value: '2d', label: '2D 角度热图' }]} /><Select aria-label="叠加波束数" value={overlay} onChange={setOverlay} options={[1, 4, 8].map((value) => ({ value, label: `${value} beam${value > 1 ? 's' : ''} overlay` }))} /><Button onClick={() => nextBeam(-1)} disabled={beamIndex === 0}>↑ 上一束</Button><Button onClick={() => nextBeam(1)} disabled={beamIndex >= ids.length - 1}>↓ 下一束</Button></Space>
    {error && <Alert type="error" title="波束加载失败" description={error} className="section-bottom" />}{busy && <Spin description="加载真实方向图" />}
    <PatternCanvas entries={entries} mode={mode} yaw={yaw} pitch={pitch} stride={stride} />
    <Space wrap className="section-top">{entries.map(({ beam }, index) => <Tag key={beam} color={COLORS[index % COLORS.length]}>Beam {beam}</Tag>)}</Space>
    {mode === '3d' && <Space wrap className="section-top"><span>水平旋转</span><Slider min={-180} max={180} value={yaw} onChange={setYaw} style={{ width: 130 }} /><span>俯仰</span><Slider min={-80} max={80} value={pitch} onChange={setPitch} style={{ width: 130 }} /><span>渲染抽样</span><Slider min={1} max={6} value={stride} onChange={setStride} style={{ width: 130 }} /></Space>}
    <Typography.Paragraph type="secondary" className="section-top">显示值为每束各自 peak-normalized 相对响应；多束仅叠加展示，不作功率合成。渲染抽样不改变后端 91×72 全网格数据或 nearest-grid 查询。来源 hash: {profile?.artifact_hash.slice(0, 16) ?? '—'}。</Typography.Paragraph>
  </Card>;
}
