import React from 'react';
import type { PhaseStats } from '../../types/neuro';
import { BAND_META } from '../../utils/format';
import { BAND_ORDER, PHASE_COLOR, PHASE_SHORT, fmtValue, linearTicks, niceMax } from './chartUtils';

interface Props {
  phases: PhaseStats[];
  unit: string | null;
}

const W = 720, H = 300, ML = 56, MR = 16, MT = 20, MB = 44;

/** Barras agrupadas: media por banda en cada fase, con ± desviación estándar entre ventanas. */
export const PhaseBandChart: React.FC<Props> = ({ phases, unit }) => {
  const usable = phases.filter(p => p.sufficient && p.bands.some(b => b.mean !== null));
  const skipped = phases.filter(p => !usable.includes(p));
  if (usable.length === 0) {
    return <p className="chart-empty">No hay datos EEG suficientes para graficar las fases{skipped[0]?.insufficient_reason ? `: ${skipped[0].insufficient_reason}` : '.'}</p>;
  }
  const counts = new Map<string, number>();
  const labeled = usable.map(p => {
    const n = (counts.get(p.kind) ?? 0) + 1;
    counts.set(p.kind, n);
    return { phase: p, label: PHASE_SHORT[p.kind] + (usable.filter(q => q.kind === p.kind).length > 1 ? ` (${n})` : '') };
  });
  const bands = BAND_ORDER.filter(band => usable.some(p => p.bands.some(b => b.band === band && b.mean !== null)));
  const top = Math.max(...usable.flatMap(p => p.bands.map(b => (b.mean ?? 0) + (b.std ?? 0))), 0);
  const yMax = niceMax(top);
  const plotW = W - ML - MR, plotH = H - MT - MB;
  const y = (v: number) => MT + plotH - (v / yMax) * plotH;
  const groupW = plotW / bands.length;
  const barW = Math.min(36, (groupW * 0.72) / labeled.length);

  return <>
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={`Media de potencia por banda en cada fase (${unit ?? 'sin unidad'}). Se detalla en la tabla inferior.`}>
      {linearTicks(yMax).map(tick => <g key={tick}>
        <line className="chart-grid" x1={ML} x2={W - MR} y1={y(tick)} y2={y(tick)} />
        <text className="chart-text" x={ML - 8} y={y(tick) + 4} textAnchor="end">{fmtValue(tick)}</text>
      </g>)}
      <line className="chart-axis" x1={ML} x2={W - MR} y1={y(0)} y2={y(0)} />
      <text className="chart-axis-title" transform={`translate(14 ${MT + plotH / 2}) rotate(-90)`} textAnchor="middle">{unit ?? 'Unidad no disponible'}</text>
      {bands.map((band, gi) => {
        const gx = ML + gi * groupW + groupW / 2;
        return <g key={band}>
          {labeled.map(({ phase, label }, bi) => {
            const stat = phase.bands.find(b => b.band === band);
            if (!stat || stat.mean === null) return null;
            const x = gx - (labeled.length * barW) / 2 + bi * barW + 2;
            const w = barW - 4;
            const yTop = y(stat.mean);
            const whiskerTop = y(stat.mean + (stat.std ?? 0));
            const whiskerBottom = y(Math.max(0, stat.mean - (stat.std ?? 0)));
            const cx = x + w / 2;
            return <g key={phase.phase_id}>
              <title>{`${label} · ${BAND_META[band].label}: ${fmtValue(stat.mean)}${stat.std !== null ? ` ± ${fmtValue(stat.std)}` : ''} (${stat.n_valid_bins} ventanas)`}</title>
              <rect x={x} y={yTop} width={w} height={Math.max(0, y(0) - yTop)} rx={3} style={{ fill: PHASE_COLOR[phase.kind] }} />
              {stat.std !== null && <>
                <line className="chart-whisker" x1={cx} x2={cx} y1={whiskerTop} y2={whiskerBottom} />
                <line className="chart-whisker" x1={cx - 4} x2={cx + 4} y1={whiskerTop} y2={whiskerTop} />
                <line className="chart-whisker" x1={cx - 4} x2={cx + 4} y1={whiskerBottom} y2={whiskerBottom} />
              </>}
              <text className="chart-text" x={cx} y={whiskerTop - 5} textAnchor="middle" fontSize="10">{fmtValue(stat.mean)}</text>
            </g>;
          })}
          <text className="chart-text strong" x={gx} y={H - 22} textAnchor="middle">{BAND_META[band].short}</text>
          <text className="chart-axis-title" x={gx} y={H - 8} textAnchor="middle">{BAND_META[band].range}</text>
        </g>;
      })}
    </svg>
    <ul className="chart-legend">
      {labeled.map(({ phase, label }) => <li key={phase.phase_id}>
        <span className="swatch" style={{ background: PHASE_COLOR[phase.kind] }} aria-hidden="true" />
        <span>{label}</span>
        <small>· calidad media de señal {phase.quality.mean_overall_quality !== null ? `${phase.quality.mean_overall_quality.toFixed(0)}%` : 'no disponible'}</small>
      </li>)}
    </ul>
    <p className="muted" style={{ margin: '10px 4px 0' }}>Las barras muestran la media de todas las mediciones registradas (sensores × ventanas de tiempo); las líneas, ± su desviación estándar. Es una descripción, no una prueba estadística.</p>
    {skipped.length > 0 && <p className="muted" style={{ margin: '6px 4px 0' }}>Sin datos suficientes en: {skipped.map(p => `${PHASE_SHORT[p.kind]}${p.insufficient_reason ? ` (${p.insufficient_reason})` : ''}`).join('; ')}.</p>}
  </>;
};
