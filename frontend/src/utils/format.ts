import type { BandKey, DataSource, PhaseKind, RealtimeFrame } from '../types/neuro';

export const BAND_META: Record<
  BandKey,
  { label: string; short: string; range: string; color: string; region: string; subtitle: string }
> = {
  theta: {
    label: 'Banda Theta',
    short: 'Theta',
    range: '4–8 Hz',
    color: '#ccbeff',
    region: 'AF3 / F3',
    subtitle: 'Actividad frontomedial exploratoria',
  },
  alpha: {
    label: 'Banda Alfa',
    short: 'Alfa',
    range: '8–12 Hz',
    color: '#d0bcff',
    region: 'O1 / O2',
    subtitle: 'Sincronía parieto-occipital en reposo',
  },
  low_beta: {
    label: 'Beta Baja',
    short: 'Beta L',
    range: '12–16 Hz',
    color: '#45dfa4',
    region: 'F3 / FC5',
    subtitle: 'Atención focalizada y vigilia tranquila',
  },
  high_beta: {
    label: 'Beta Alta',
    short: 'Beta H',
    range: '16–25 Hz',
    color: '#a078ff',
    region: 'AF4 / F4',
    subtitle: 'Procesamiento cognitivo activo',
  },
  gamma: {
    label: 'Banda Gamma',
    short: 'Gamma',
    range: '25–45 Hz',
    color: '#f472b6',
    region: 'T7 / T8',
    subtitle: 'Integración multisensorial de alta frecuencia',
  },
};

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
    return '00:00';
  }
  const total = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hrs > 0) {
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function formatClockHMS(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function formatSourceLabel(source: DataSource): string {
  switch (source) {
    case 'SIMULATED':
      return 'DATOS SIMULADOS';
    case 'VIRTUAL_DEVICE':
      return 'DISPOSITIVO VIRTUAL';
    case 'REAL_EMOTIV':
      return 'EMOTIV CORTEX REAL';
    case 'DISCONNECTED':
    default:
      return 'DESCONECTADO';
  }
}

export function formatPhaseKind(kind: PhaseKind): string {
  switch (kind) {
    case 'BASELINE':
      return 'Referencia Inicial (Línea Base)';
    case 'MATH':
      return 'Actividad Cognitiva (NeuroTest)';
    case 'REGULATION':
      return 'Autorregulación Guiada (NeuroCalma)';
  }
}

export function computeBandAverage(
  frame: RealtimeFrame | null,
  band: BandKey
): number | null {
  if (!frame || !frame.pow) return null;
  const vals: number[] = [];
  for (const sensor of Object.keys(frame.pow)) {
    const v = frame.pow[sensor]?.[band];
    if (typeof v === 'number' && Number.isFinite(v)) {
      vals.push(v);
    }
  }
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

export function countActiveSensors(frame: RealtimeFrame | null): {
  good: number;
  total: number;
} {
  if (!frame) return { good: 0, total: 0 };
  const qMap = Object.keys(frame.quality).length > 0 ? frame.quality : frame.contact;
  const keys = Object.keys(qMap);
  if (keys.length === 0) {
    const powKeys = Object.keys(frame.pow || {});
    return { good: 0, total: powKeys.length };
  }
  const good = keys.filter((k) => (qMap[k] ?? 0) >= 3).length;
  return { good, total: keys.length };
}

