import type { BandKey, RealtimeFrame, SensorLayout } from '../../types/neuro';
export type SensorColorMode = 'power' | 'quality';
export interface SensorReading {
  id: string; x: number; y: number; value: number | null;
  contact: number | null; quality: number | null; color: string;
}
export function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
export function sensorReadings(layout: SensorLayout | null, frame: RealtimeFrame | null, band: BandKey, mode: SensorColorMode, ceiling: number): SensorReading[] {
  return (layout?.sensors ?? []).map(sensor => {
    const value = finite(frame?.pow?.[sensor.id]?.[band]);
    const quality = finite(frame?.quality?.[sensor.id]);
    const contact = finite(frame?.contact?.[sensor.id]);
    const magnitude = mode === 'quality' ? quality ?? contact : value;
    const ratio = Math.min(1, Math.max(0, (magnitude ?? 0) / Math.max(ceiling, .001)));
    return { ...sensor, value, quality, contact,
      color: magnitude === null ? '#97929f' : mode === 'quality' ? ['#b75e70', '#be8156', '#b49a51', '#5d9d84', '#39846d'][Math.round(ratio * 4)] : `hsl(262, 48%, ${88 - 52 * ratio}%)` };
  });
}
/** Existing 10-20 projection, explicitly approximated onto an upper head ellipsoid.
 * +X = participant right, +Y = superior, +Z = front. No cortical localization. */
export function cranialPosition(x: number, y: number): [number, number, number] {
  return [x, Math.sqrt(Math.max(.02, 1 - x * x - y * y)) * .95, y * 1.15];
}
export function sensorRegion(id: string): string {
  if (/^(AF|F|FC)/.test(id)) return 'Posición anterior del cuero cabelludo';
  if (/^O/.test(id)) return 'Posición posterior del cuero cabelludo';
  if (/^P/.test(id)) return 'Posición parietal/posterior del cuero cabelludo';
  if (/^T/.test(id)) return 'Posición lateral del cuero cabelludo';
  return 'Posición aproximada del montaje';
}
