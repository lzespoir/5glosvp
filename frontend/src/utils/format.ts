import dayjs from 'dayjs';

export const EMPTY = '—';

export function isNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

export function formatSeconds(v: number | null | undefined, digits = 3): string {
  return isNumber(v) ? `${v.toFixed(digits)} s` : EMPTY;
}

/** 频率/带宽：Hz → GHz / MHz / kHz */
export function formatHz(v: number | null | undefined): string {
  if (!isNumber(v)) return EMPTY;
  const units: [number, string][] = [
    [1e9, 'GHz'],
    [1e6, 'MHz'],
    [1e3, 'kHz'],
  ];
  for (const [scale, unit] of units) {
    if (Math.abs(v) >= scale) return `${trimNumber(v / scale)} ${unit}`;
  }
  return `${trimNumber(v)} Hz`;
}

export function trimNumber(v: number, maxDigits = 3): string {
  return Number(v.toFixed(maxDigits)).toString();
}

export function formatValue(v: number | null | undefined, unit?: string | null, digits = 1): string {
  if (!isNumber(v)) return EMPTY;
  return unit ? `${v.toFixed(digits)} ${unit}` : v.toFixed(digits);
}

export function formatPercent(ratio: number | null | undefined, digits = 1): string {
  return isNumber(ratio) ? `${(ratio * 100).toFixed(digits)}%` : EMPTY;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return EMPTY;
  const d = dayjs(iso);
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : EMPTY;
}

export function formatVector(v: number[] | null | undefined, unit?: string, digits = 2): string {
  if (!v || v.length === 0 || !v.every(isNumber)) return EMPTY;
  const body = `(${v.map((x) => trimNumber(x, digits)).join(', ')})`;
  return unit ? `${body} ${unit}` : body;
}
