import React, { useMemo, useState } from 'react';
import type { BandKey, PhaseStats, TimeseriesOut } from '../../types/neuro';
import { BAND_META } from '../../utils/format';
import { PHASE_COLOR, PHASE_SHORT, fmtValue, linearTicks, niceMax } from './chartUtils';

interface Props {
  series: TimeseriesOut;
  phases: PhaseStats[];
  band: BandKey;
}

const W = 720, H = 300, ML = 56, MR = 16, MT = 18, MB = 46;

/**
 * Evolución temporal de una banda. No interpola: la línea se corta donde faltan datos
 * (valor ausente o salto temporal mayor que 2,5 ventanas), y las fases se sombrean por su phase_id.
 */
export const TimeseriesChart: React.FC<Props> = ({ series, phases, band }) => {
  const [hover, setHover] = useState<number | null>(null);
  const kindById = useMemo(() => new Map(phases.map(p => [p.phase_id, p.kind])), [phases]);
  const pts = series.points;
  const valid = pts.filter(p => typeof p.values[band] === 'number' && Number.isFinite(p.values[band] as number));

  if (valid.length < 2) return <p className="chart-empty">No hay suficientes datos de {BAND_META[band].label.toLowerCase()} para dibujar su evolución.</p>;

  const tMin = Math.min(...pts.map(p => p.t));
  const tMax = Math.max(...pts.map(p => p.t)) + series.bin_seconds;
  const yMax = niceMax(Math.max(...valid.map(p => p.values[band] as number)));
  const plotW = W - ML - MR, plotH = H - MT - MB;
  const x = (t: number) => ML + ((t - tMin) / Math.max(tMax - tMin, 1)) * plotW;
  const y = (v: number) => MT + plotH - (v / yMax) * plotH;

  // Segmentos continuos de la línea
  const maxGap = series.bin_seconds * 2.5;
  let d = '';
  let prev: number | null = null;
  for (const p of pts) {
    const v = p.values[band];
    if (typeof v !== 'number' || !Number.isFinite(v)) { prev = null; continue; }
    d += `${prev === null || p.t - prev > maxGap ? 'M' : 'L'}${x(p.t).toFixed(1)},${y(v).toFixed(1)} `;
    prev = p.t;
  }

  // Bandas de fase (carreras contiguas con el mismo phase_id)
  const runs: { id: number; from: number; to: number }[] = [];
  for (const p of pts) {
    if (p.phase_id === null) continue;
    const last = runs[runs.length - 1];
    if (last && last.id === p.phase_id) last.to = p.t + series.bin_seconds;
    else runs.push({ id: p.phase_id, from: p.t, to: p.t + series.bin_seconds });
  }
  const usedKinds = Array.from(new Set(runs.map(r => kindById.get(r.id)).filter(Boolean))) as (keyof typeof PHASE_SHORT)[];

  const xTicks = 5;
  const onMove = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * W;
    const t = tMin + ((px - ML) / plotW) * (tMax - tMin);
    let best = -1, bestDist = Infinity;
    valid.forEach((p, i) => { const dist = Math.abs(p.t - t); if (dist < bestDist) { best = i; bestDist = dist; } });
    setHover(best >= 0 ? best : null);
  };
  const hp = hover !== null ? valid[hover] : null;
  const hpKind = hp?.phase_id != null ? kindById.get(hp.phase_id) : undefined;

  return <>
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" onMouseMove={onMove} onMouseLeave={() => setHover(null)}
      aria-label={`Evolución de la ${BAND_META[band].label.toLowerCase()} durante la sesión, con ${valid.length} ventanas con datos.`}>
      {runs.map((r, i) => {
        const kind = kindById.get(r.id);
        return <rect key={`${r.id}-${i}`} x={x(r.from)} y={MT} width={Math.max(1, x(r.to) - x(r.from))} height={plotH}
          style={{ fill: kind ? PHASE_COLOR[kind] : 'var(--border)', opacity: 0.16 }}><title>{kind ? PHASE_SHORT[kind] : 'Fase'}</title></rect>;
      })}
      {linearTicks(yMax).map(tick => <g key={tick}>
        <line className="chart-grid" x1={ML} x2={W - MR} y1={y(tick)} y2={y(tick)} />
        <text className="chart-text" x={ML - 8} y={y(tick) + 4} textAnchor="end">{fmtValue(tick)}</text>
      </g>)}
      <line className="chart-axis" x1={ML} x2={W - MR} y1={y(0)} y2={y(0)} />
      {Array.from({ length: xTicks + 1 }, (_, i) => tMin + ((tMax - tMin) * i) / xTicks).map(t => <text key={t} className="chart-text" x={x(t)} y={H - 24} textAnchor="middle">{Math.round(t)} s</text>)}
      <text className="chart-axis-title" x={ML + plotW / 2} y={H - 8} textAnchor="middle">Tiempo desde el inicio de la sesión</text>
      <text className="chart-axis-title" transform={`translate(14 ${MT + plotH / 2}) rotate(-90)`} textAnchor="middle">{series.unit ?? 'Unidad no disponible'}</text>
      <path d={d.trim()} fill="none" strokeWidth={2.2} strokeLinejoin="round" strokeLinecap="round" style={{ stroke: 'var(--chart-line)' }} />
      {hp && <g>
        <line className="chart-cursor" x1={x(hp.t)} x2={x(hp.t)} y1={MT} y2={y(0)} />
        <circle cx={x(hp.t)} cy={y(hp.values[band] as number)} r={5} strokeWidth={2.5} style={{ fill: 'var(--surface)', stroke: 'var(--chart-line)' }} />
      </g>}
    </svg>
    <div className="chart-readout" role="status" aria-live="off">
      {hp ? `t = ${Math.round(hp.t)} s · ${BAND_META[band].short}: ${fmtValue(hp.values[band] as number)} ${series.unit ?? ''}${hpKind ? ` · ${PHASE_SHORT[hpKind]}` : ''}` : 'Pasa el cursor por la gráfica para ver el valor de cada instante.'}
    </div>
    {usedKinds.length > 0 && <ul className="chart-legend">
      {usedKinds.map(kind => <li key={kind}><span className="swatch" style={{ background: PHASE_COLOR[kind], opacity: 0.55 }} aria-hidden="true" />{PHASE_SHORT[kind]}</li>)}
    </ul>}
    <p className="muted" style={{ margin: '10px 4px 0' }}>Media de todos los sensores por ventana de {series.bin_seconds} s. Los cortes en la línea indican datos ausentes: no se rellenan ni se estiman.</p>
  </>;
};

