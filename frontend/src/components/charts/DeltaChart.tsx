import React from 'react';
import type { BandDelta } from '../../types/neuro';
import { BAND_META } from '../../utils/format';
import { BAND_ORDER, fmtPercent, niceMax } from './chartUtils';

interface Props {
  deltas: BandDelta[];
  labelA: string;
  labelB: string;
}

const W = 720, ML = 130, MR = 70, ROW = 40, MT = 26, MB = 30;

/** Barras divergentes: cambio porcentual de la fase B respecto a la fase A, por banda. */
export const DeltaChart: React.FC<Props> = ({ deltas, labelA, labelB }) => {
  const rows = BAND_ORDER.map(band => deltas.find(d => d.band === band)).filter((d): d is BandDelta => !!d);
  if (rows.length === 0) return <p className="chart-empty">No hay cambios que mostrar.</p>;
  const maxAbs = niceMax(Math.max(10, ...rows.map(d => Math.abs(d.percent_change ?? 0))));
  const H = MT + rows.length * ROW + MB;
  const plotW = W - ML - MR;
  const zeroX = ML + plotW / 2;
  const scale = (plotW / 2) / maxAbs;

  return <>
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={`Cambio porcentual por banda de ${labelB} respecto a ${labelA}. Los valores exactos están en la tabla inferior.`}>
      {[-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs].map(tick => <g key={tick}>
        <line className={tick === 0 ? 'chart-axis' : 'chart-grid'} x1={zeroX + tick * scale} x2={zeroX + tick * scale} y1={MT - 8} y2={H - MB + 4} />
        <text className="chart-text" x={zeroX + tick * scale} y={H - 10} textAnchor="middle">{tick > 0 ? '+' : ''}{Number.isInteger(tick) ? tick : tick.toFixed(1)}%</text>
      </g>)}
      {rows.map((d, i) => {
        const cy = MT + i * ROW + ROW / 2;
        const pct = d.percent_change;
        const w = pct === null ? 0 : Math.abs(pct) * scale;
        const up = (pct ?? 0) >= 0;
        return <g key={d.band}>
          <title>{`${BAND_META[d.band].label}: ${fmtPercent(pct)} (de ${d.mean_a?.toFixed(2) ?? '—'} a ${d.mean_b?.toFixed(2) ?? '—'})`}</title>
          <text className="chart-text strong" x={ML - 12} y={cy - 2} textAnchor="end">{BAND_META[d.band].short}</text>
          <text className="chart-axis-title" x={ML - 12} y={cy + 11} textAnchor="end">{BAND_META[d.band].range}</text>
          {pct !== null && <rect x={up ? zeroX : zeroX - w} y={cy - 11} width={Math.max(w, 1)} height={22} rx={3}
            style={{ fill: up ? 'var(--chart-inc)' : 'var(--chart-dec)' }} />}
          <text className={`chart-text strong ${pct === null ? '' : up ? 'delta-up' : 'delta-down'}`} x={pct === null ? zeroX + 8 : up ? zeroX + w + 8 : zeroX - w - 8} y={cy + 4} textAnchor={up || pct === null ? 'start' : 'end'}>
            {pct === null ? '— (sin base)' : `${up ? '▲' : '▼'} ${fmtPercent(pct)}`}
          </text>
        </g>;
      })}
    </svg>
    <ul className="chart-legend">
      <li><span className="swatch" style={{ background: 'var(--chart-inc)' }} aria-hidden="true" />▲ Mayor en «{labelB}» que en «{labelA}»</li>
      <li><span className="swatch" style={{ background: 'var(--chart-dec)' }} aria-hidden="true" />▼ Menor en «{labelB}» que en «{labelA}»</li>
    </ul>
    <p className="muted" style={{ margin: '10px 4px 0' }}>Cambio relativo a la media de «{labelA}». Un aumento o una disminución no es «mejor» ni «peor»: solo describe una diferencia de potencia.</p>
  </>;
};

