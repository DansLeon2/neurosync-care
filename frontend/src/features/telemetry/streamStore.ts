import type { HistoryPoint, RealtimeFrame, DataSource, BandKey } from '../../types/neuro';
import { computeBandAverage } from '../../utils/format';
import { CircularBuffer } from './buffer';

const bands: BandKey[] = ['theta', 'alpha', 'low_beta', 'high_beta', 'gamma'];
const buffer = new CircularBuffer<HistoryPoint>(1024);
const listeners = new Set<() => void>();
let frame: RealtimeFrame | null = null;
let source: DataSource | null = null;
let timer: ReturnType<typeof setTimeout> | undefined;
let snapshot: { frame: RealtimeFrame | null; history: HistoryPoint[] } = { frame: null, history: [] };

function publish() {
  timer = undefined;
  snapshot = { frame, history: buffer.snapshot() };
  listeners.forEach(listener => listener());
}

export const telemetry = {
  subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
  getSnapshot: () => snapshot,
  ingest(value: RealtimeFrame) {
    if (source !== null && source !== value.source) buffer.clear();
    source = value.source;
    frame = value;
    buffer.push({ seq: value.seq, timestamp: value.timestamp, source: value.source, pow_unit: value.pow_unit,
      pow: value.pow, bands: Object.fromEntries(bands.map(band => [band, computeBandAverage(value, band)])) as Record<BandKey, number | null>,
      channels: {}, overall_quality: value.overall_quality });
    // Se guardan TODOS los fotogramas recibidos; solo se agrupan notificaciones de UI.
    if (timer === undefined) timer = setTimeout(publish, 125);
  },
  gap() {
    frame = null;
    buffer.push({ seq: -1, timestamp: new Date().toISOString(), source: source ?? 'DISCONNECTED', pow_unit: null,
      pow: {}, bands: { theta: null, alpha: null, low_beta: null, high_beta: null, gamma: null }, channels: {}, overall_quality: null });
    if (timer !== undefined) clearTimeout(timer);
    publish();
  },
  clear() {
    frame = null; source = null; buffer.clear();
    if (timer !== undefined) clearTimeout(timer);
    publish();
  },
  flush() { if (timer !== undefined) clearTimeout(timer); publish(); },
};
