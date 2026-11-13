import { useState } from 'react';
import type { BandKey, HistoryPoint } from '../../types/neuro';
import { BAND_META } from '../../utils/format';
import { niceMax, fmtValue, linearTicks } from '../../components/charts/chartUtils';
import { linePath, selectedValue } from './chartModel';
const COLORS = { theta: '#8394bc', alpha: '#9573c5', low_beta: '#ce9855', high_beta: '#be6a89', gamma: '#429e8d' };
const W = 560, H = 255, L = 62, R = 18, T = 22, B = 46;
export function LiveBandChart({ points, band, sensor, seconds, unit }: { points: HistoryPoint[]; band: BandKey; sensor: string; seconds: number; unit: string | null }) {
  const [extra, setExtra] = useState<BandKey[]>([]);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const bands = [band, ...extra.filter(value => value !== band)];
  const end = points.length ? Date.parse(points[points.length - 1].timestamp) : Date.now();
  const start = end - seconds * 1000;
  const visible = points.filter(point => Date.parse(point.timestamp) >= start);
  const values = visible.flatMap(point => bands.map(key => selectedValue(point, key, sensor))).filter((value): value is number => value !== null);
  const max = niceMax(Math.max(...values, 1));
  const x = (time: number) => L + (time - start) / (end - start) * (W - L - R);
  const y = (value: number) => H - B - value / max * (H - B - T);
  const hover = hoverTime === null ? null : visible.reduce<HistoryPoint | null>((best, point) => !best || Math.abs(Date.parse(point.timestamp) - hoverTime) < Math.abs(Date.parse(best.timestamp) - hoverTime) ? point : best, null);
  return <div className="live-chart">
    {values.length < 2 ? <div className="chart-empty">Esperando muestras de {BAND_META[band].label}. Los datos ausentes no se estiman.</div> : <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" tabIndex={0} aria-label={`Evolución de potencia ${BAND_META[band].label}, ${sensor === 'ALL' ? 'media entre sensores' : sensor}`}
      onPointerMove={event => { const rect = event.currentTarget.getBoundingClientRect(); const position = (event.clientX - rect.left) / rect.width * W; setHoverTime(start + Math.max(0, Math.min(1, (position - L) / (W - L - R))) * (end - start)); }}
      onPointerLeave={() => setHoverTime(null)} onKeyDown={event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); setHoverTime(time => Math.max(start, Math.min(end, (time ?? end) + (event.key === 'ArrowLeft' ? -1000 : 1000)))); } }}>
      {linearTicks(max).map(tick => <g key={tick}><line className="chart-grid" x1={L} x2={W-R} y1={y(tick)} y2={y(tick)} /><text className="chart-text" x={L-10} y={y(tick)+4} textAnchor="end">{fmtValue(tick)}</text></g>)}
      {[0, .25, .5, .75, 1].map(ratio => <text className="chart-text" key={ratio} x={x(start + ratio * (end-start))} y={H-25} textAnchor="middle">−{Math.round(seconds * (1-ratio))} s</text>)}
      <text className="chart-axis-title" x={W/2} y={H-6} textAnchor="middle">Ventana reciente · {unit ?? 'sin unidad disponible'}</text>
      {bands.map(key => <path key={key} d={linePath(visible, key, sensor, x, y)} stroke={COLORS[key]} fill="none" strokeWidth={key === band ? 2.5 : 1.7} strokeDasharray={key === band ? undefined : '5 3'} />)}
      {hover && <line className="chart-cursor" x1={x(Date.parse(hover.timestamp))} x2={x(Date.parse(hover.timestamp))} y1={T} y2={H-B} />}
    </svg>}
    <div className="chart-readout" role="status" aria-live="off">{hover ? `${new Date(hover.timestamp).toLocaleTimeString('es', { hour12: false })} · ${bands.map(key => `${BAND_META[key].short}: ${selectedValue(hover, key, sensor)?.toFixed(2) ?? '—'}`).join(' · ')} ${unit ?? ''}` : 'Consulta con el cursor o enfoca la gráfica y usa ← →. Los cortes indican ausencia de datos.'}</div>
    <div className="interactive-legend" role="group" aria-label="Bandas adicionales">{(Object.keys(COLORS) as BandKey[]).map(key => <button type="button" key={key} aria-pressed={bands.includes(key)} disabled={key === band} onClick={() => setExtra(previous => previous.includes(key) ? previous.filter(value => value !== key) : [...previous, key])}><span className="swatch" style={{ background: COLORS[key] }} />{BAND_META[key].short}</button>)}</div>
  </div>;
}
