import type { BandKey, HistoryPoint } from '../../types/neuro';
export function selectedValue(point: HistoryPoint, band: BandKey, sensor: string): number | null {
  const value = sensor === 'ALL' ? point.bands[band] : point.pow[sensor]?.[band];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
export function linePath(points: HistoryPoint[], band: BandKey, sensor: string, x: (time: number) => number, y: (value: number) => number): string {
  let previous: HistoryPoint | null = null;
  let path = '';
  for (const point of points) {
    const value = selectedValue(point, band, sensor);
    if (value === null) { previous = null; continue; }
    const time = Date.parse(point.timestamp);
    const gap = !previous || time - Date.parse(previous.timestamp) > 500 || previous.source !== point.source || previous.pow_unit !== point.pow_unit;
    path += `${gap ? 'M' : 'L'}${x(time).toFixed(1)},${y(value).toFixed(1)} `;
    previous = point;
  }
  return path.trim();
}
