import React from 'react';
import type { SelfReportSummary } from './reportTypes';
import { MOMENT_SHORT } from './chartUtils';

interface Props {
  reports: SelfReportSummary[];
}

const W = 720, H = 240, ML = 44, MR = 30, MT = 20, MB = 52;

/** Evolución de la tensión percibida (0–10) en los momentos registrados por la persona. */
export const TensionChart: React.FC<Props> = ({ reports }) => {
  if (reports.length === 0) return <p className="chart-empty">No se registraron autoevaluaciones.</p>;
  const sorted = [...reports].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const plotW = W - ML - MR, plotH = H - MT - MB;
  const x = (i: number) => sorted.length === 1 ? ML + plotW / 2 : ML + (i / (sorted.length - 1)) * plotW;
  const y = (v: number) => MT + plotH - (v / 10) * plotH;
  const path = sorted.map((r, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(r.tension).toFixed(1)}`).join(' ');

  return <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img"
    aria-label={`Tensión percibida: ${sorted.map(r => `${MOMENT_SHORT[r.moment] ?? r.moment} ${r.tension} de 10`).join(', ')}.`}>
    {[0, 2, 4, 6, 8, 10].map(tick => <g key={tick}>
      <line className="chart-grid" x1={ML} x2={W - MR} y1={y(tick)} y2={y(tick)} />
      <text className="chart-text" x={ML - 8} y={y(tick) + 4} textAnchor="end">{tick}</text>
    </g>)}
    {sorted.length > 1 && <path d={path} fill="none" strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" style={{ stroke: 'var(--chart-line)' }} />}
    {sorted.map((r, i) => <g key={`${r.moment}-${i}`}>
      <title>{`${MOMENT_SHORT[r.moment] ?? r.moment}: ${r.tension} / 10`}</title>
      <circle cx={x(i)} cy={y(r.tension)} r={7} strokeWidth={3} style={{ fill: 'var(--surface)', stroke: 'var(--chart-line)' }} />
      <text className="chart-text strong" x={x(i)} y={y(r.tension) - 14} textAnchor="middle">{r.tension}</text>
      <text className="chart-text" x={x(i)} y={H - 24} textAnchor="middle">{MOMENT_SHORT[r.moment] ?? r.moment}</text>
    </g>)}
    <text className="chart-axis-title" x={ML - 30} y={MT - 6}>Tensión percibida (0–10)</text>
  </svg>;
};

