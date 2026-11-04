import type { BandKey, PhaseKind } from '../../types/neuro';

export const BAND_ORDER: BandKey[] = ['theta', 'alpha', 'low_beta', 'high_beta', 'gamma'];

export const PHASE_COLOR: Record<PhaseKind, string> = {
  BASELINE: 'var(--phase-baseline)',
  MATH: 'var(--phase-math)',
  REGULATION: 'var(--phase-reg)',
};

/** Etiquetas cortas, neutrales y comprensibles para voluntarios. */
export const PHASE_SHORT: Record<PhaseKind, string> = {
  BASELINE: 'Referencia inicial',
  MATH: 'Operaciones',
  REGULATION: 'Calma guiada',
};

export const MOMENT_SHORT: Record<string, string> = {
  INITIAL: 'Al inicio',
  POST_MATH: 'Tras las operaciones',
  FINAL: 'Al terminar',
  OTHER: 'Otro momento',
};

/** Máximo “redondo” para el eje Y (1, 2, 2.5, 5, 10 × 10^n). */
export function niceMax(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1;
  const exp = Math.pow(10, Math.floor(Math.log10(value)));
  const f = value / exp;
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
  return nice * exp;
}

export function linearTicks(max: number, count = 4): number[] {
  return Array.from({ length: count + 1 }, (_, i) => (max * i) / count);
}

export function fmtValue(v: number): string {
  const a = Math.abs(v);
  if (a >= 100) return v.toFixed(0);
  if (a >= 10) return v.toFixed(1);
  return v.toFixed(2);
}

export function fmtPercent(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—';
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`;
}

