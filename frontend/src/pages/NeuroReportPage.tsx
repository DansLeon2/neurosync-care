import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { BandKey, PhaseComparison, PhaseKind, SessionListItem, SessionSummary, TimeseriesOut } from '../types/neuro';
import { BAND_META, formatDuration, formatPhaseKind, formatSourceLabel } from '../utils/format';
import { BAND_ORDER, MOMENT_SHORT, PHASE_SHORT, fmtPercent } from '../components/charts/chartUtils';
import { PhaseBandChart } from '../components/charts/PhaseBandChart';
import { DeltaChart } from '../components/charts/DeltaChart';
import { TimeseriesChart } from '../components/charts/TimeseriesChart';
import { TensionChart } from '../components/charts/TensionChart';

interface Props { selectedSessionId: number | null; onSelectSessionId: (id: number | null) => void; temporarySessionId: number | null; onCloseTemporary: () => void; }

const PHASE_KINDS: PhaseKind[] = ['BASELINE', 'MATH', 'REGULATION'];
const signed = (n: number) => (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n);

export const NeuroReportPage: React.FC<Props> = ({ selectedSessionId, onSelectSessionId, temporarySessionId, onCloseTemporary }) => {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [comparison, setComparison] = useState<PhaseComparison | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesOut | null>(null);
  const [phaseA, setPhaseA] = useState<PhaseKind>('BASELINE');
  const [phaseB, setPhaseB] = useState<PhaseKind>('REGULATION');
  const [band, setBand] = useState<BandKey>('alpha');
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    api.listSessions().then(list => {
      if (!alive) return;
      setSessions(list);
      if (selectedSessionId === null && list.length) onSelectSessionId(list[0].id);
    }).catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, [revision, selectedSessionId, onSelectSessionId]);

  // Resumen y serie temporal: dependen solo de la sesión (no parpadean al cambiar de fases).
  useEffect(() => {
    let alive = true;
    setSummary(null); setComparison(null); setTimeseries(null); setError('');
    if (selectedSessionId === null) return;
    setBusy(true);
    Promise.all([api.getSessionSummary(selectedSessionId), api.getSessionTimeseries(selectedSessionId)])
      .then(([sum, ts]) => { if (alive) { setSummary(sum); setTimeseries(ts); } })
      .catch(err => { if (alive) setError((err as Error).message); })
      .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [selectedSessionId, revision]);

  // Comparación entre dos fases: se recalcula al elegir otras.
  useEffect(() => {
    let alive = true;
    if (selectedSessionId === null) return;
    api.comparePhases(selectedSessionId, phaseA, phaseB)
      .then(cmp => { if (alive) setComparison(cmp); })
      .catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, [selectedSessionId, phaseA, phaseB, revision]);

  // Si la sesión no tiene alguna de las fases elegidas, se proponen las dos primeras que existan.
  const presentKinds = useMemo(() => Array.from(new Set((summary?.phases ?? []).map(p => p.kind))), [summary]);
  useEffect(() => {
    if (presentKinds.length >= 2 && (!presentKinds.includes(phaseA) || !presentKinds.includes(phaseB))) {
      setPhaseA(presentKinds[0]); setPhaseB(presentKinds[1]);
    }
  }, [presentKinds, phaseA, phaseB]);

  const pickPhase = (which: 'A' | 'B', value: PhaseKind) => {
    // Nunca se comparan dos fases iguales: si coincide, se intercambian.
    if (which === 'A') { if (value === phaseB) setPhaseB(phaseA); setPhaseA(value); }
    else { if (value === phaseA) setPhaseA(phaseB); setPhaseB(value); }
  };

  const remove = async (id: number | null) => {
    if (!window.confirm(id === null ? '¿Eliminar todo el historial local? Esta acción no se puede deshacer.' : '¿Eliminar esta sesión del historial local?')) return;
    setBusy(true); setError('');
    try {
      if (id === null) await api.deleteAllSessions(); else await api.deleteSession(id);
      onSelectSessionId(null); setRevision(value => value + 1);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };

  const finalChange = summary?.tension_changes.find(change => change.from_moment === 'INITIAL' && change.to_moment === 'FINAL');
  const math = summary?.math ?? null;
  const labelA = PHASE_SHORT[phaseA], labelB = PHASE_SHORT[phaseB];
  const hasWellbeingExtras = summary?.self_reports.some(r => r.difficulty !== null || r.comfort !== null) ?? false;

  return <div className="workspace report-workspace">
    <div className="page-title"><span className="eyebrow">Resultados</span><h1>Tu sesión, en perspectiva.</h1><p>Un resumen de tus respuestas y de los datos disponibles.</p></div>
    {temporarySessionId !== null && <div className="notice no-print"><strong>Resultado temporal.</strong> No aparece en el historial. Puedes exportarlo antes de cerrar.
      <button className="text-button" onClick={onCloseTemporary}>Cerrar resultados y descartar</button></div>}
    <div className="report-toolbar no-print"><label className="field-label">Sesión<select value={selectedSessionId ?? ''} onChange={event => onSelectSessionId(event.target.value ? Number(event.target.value) : null)}>
      <option value="">Selecciona una sesión</option>
      {temporarySessionId !== null && <option value={temporarySessionId}>Sesión temporal #{temporarySessionId}</option>}
      {sessions.map(session => <option key={session.id} value={session.id}>#{session.id} · {new Date(session.started_at).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })} · {session.status === 'ACTIVE' ? 'En curso' : session.status === 'ABORTED' ? 'Interrumpida' : 'Completada'}</option>)}
    </select></label><button className="button subtle" disabled={busy} onClick={() => setRevision(value => value + 1)}>Actualizar</button></div>
    {error && <p className="error-message" role="alert">{error}</p>}
    {busy && <p role="status">Cargando resultados…</p>}
    {!summary && !busy && !error && <section className="panel empty-state"><h2>Aún no hay resultados para mostrar</h2><p>Completa una sesión y vuelve aquí para revisar tu resumen.</p></section>}
    {summary && <>
      <section className="panel"><div className="section-top"><div><span className="eyebrow">Sesión #{summary.session_id}</span><h2>{summary.status === 'ABORTED' ? 'Sesión interrumpida' : summary.status === 'ACTIVE' ? 'Sesión en curso' : 'Sesión completada'}</h2></div><span className="pill">{formatSourceLabel(summary.data_source as SessionListItem['data_source'])}</span></div>
        {summary.mixed_sources && <p className="error-message">Esta sesión contiene fuentes distintas. Considera esta limitación al comparar fases.</p>}
        {summary.simulated_data && <p className="muted">Incluye datos sintéticos. Los valores EEG no representan mediciones de una persona.</p>}
        <div className="summary-grid"><div><span>Duración</span><strong>{formatDuration(summary.duration_s)}</strong></div><div><span>Operaciones</span><strong>{math?.n_questions ?? '—'}</strong></div><div><span>Aciertos</span><strong>{math?.accuracy_pct == null ? '—' : math.accuracy_pct.toFixed(1) + '%'}</strong></div><div><span>Cambio de tensión percibida</span><strong>{finalChange ? signed(finalChange.change) : '—'}</strong></div></div>
        {math && <div className="kpi-row">
          <div className="kpi"><span>Respondidas</span><strong>{math.n_answered}</strong></div>
          <div className="kpi"><span>Omitidas</span><strong>{math.n_skipped}</strong></div>
          <div className="kpi"><span>Tiempo medio de respuesta</span><strong>{math.mean_response_time_ms == null ? '—' : (math.mean_response_time_ms / 1000).toFixed(1) + ' s'}</strong></div>
          <div className="kpi"><span>Mediana de respuesta</span><strong>{math.median_response_time_ms == null ? '—' : (math.median_response_time_ms / 1000).toFixed(1) + ' s'}</strong></div>
        </div>}
        <p className="muted">Aciertos = correctas / operaciones enviadas, incluidas las omitidas. El cambio de tensión se expresa en puntos de 0 a 10, según tus respuestas.</p>
      </section>

      <section className="panel"><h2>Cómo describiste la experiencia</h2>
        {summary.self_reports.length ? <>
          <div className="chart-card"><TensionChart reports={summary.self_reports} /></div>
          {summary.tension_changes.length > 0 && <ul className="chart-legend" style={{ marginTop: 16 }}>
            {summary.tension_changes.map(change => <li key={change.label}><strong>{change.label}:</strong> {signed(change.change)} {Math.abs(change.change) === 1 ? 'punto' : 'puntos'}</li>)}
          </ul>}
          {hasWellbeingExtras && <div className="table-scroll"><table><thead><tr><th>Momento</th><th>Tensión</th><th>Dificultad</th><th>Comodidad</th></tr></thead>
            <tbody>{summary.self_reports.map((r, i) => <tr key={i}><td>{MOMENT_SHORT[r.moment] ?? r.moment}</td><td>{r.tension} / 10</td><td>{r.difficulty ?? '—'}</td><td>{r.comfort ?? '—'}</td></tr>)}</tbody></table></div>}
        </> : <p>No se registraron autoevaluaciones.</p>}
        <p className="muted">Estos valores son percepciones personales. No se deducen del EEG.</p>
      </section>

      <section className="panel" aria-labelledby="compare-title"><span className="eyebrow">Comparativa</span><h2 id="compare-title">Comparar fases de la sesión</h2>
        <p>Una mirada descriptiva a los datos EEG disponibles en cada fase. Sirve para explorar, no para sacar conclusiones sobre ti.</p>
        {summary.simulated_data && <p className="muted">Datos sintéticos: los patrones mostrados son ficticios y solo sirven para probar la plataforma.</p>}

        <div className="chart-block"><h3>Potencia por banda en cada fase</h3>
          <p>Compara las {summary.phases.length > 2 ? 'fases' : 'dos fases'} de un vistazo. Cada color es una fase.</p>
          <div className="chart-card"><PhaseBandChart phases={summary.phases} unit={timeseries?.unit ?? null} /></div>
        </div>

        <div className="chart-block"><h3>Cambio entre dos fases</h3>
          <div className="compare-controls no-print">
            <label className="field-label">Fase de referencia<select value={phaseA} onChange={event => pickPhase('A', event.target.value as PhaseKind)}>
              {PHASE_KINDS.map(kind => <option key={kind} value={kind} disabled={presentKinds.length > 0 && !presentKinds.includes(kind)}>{PHASE_SHORT[kind]}</option>)}</select></label>
            <span className="compare-arrow" aria-hidden="true">→</span>
            <label className="field-label">Fase comparada<select value={phaseB} onChange={event => pickPhase('B', event.target.value as PhaseKind)}>
              {PHASE_KINDS.map(kind => <option key={kind} value={kind} disabled={presentKinds.length > 0 && !presentKinds.includes(kind)}>{PHASE_SHORT[kind]}</option>)}</select></label>
          </div>
          <div className="chart-card" style={{ marginTop: 16 }}>
            {comparison?.available
              ? <DeltaChart deltas={comparison.deltas} labelA={labelA} labelB={labelB} />
              : <p className="chart-empty">{comparison ? (comparison.reason ?? 'Comparación no disponible.') : 'Calculando comparación…'}</p>}
          </div>
        </div>

        <div className="chart-block"><h3>Evolución durante la sesión</h3>
          <div className="band-chips no-print" role="group" aria-label="Banda de frecuencia">
            {BAND_ORDER.map(key => <button key={key} type="button" aria-pressed={band === key} onClick={() => setBand(key)}>{BAND_META[key].short} · {BAND_META[key].range}</button>)}
          </div>
          <div className="chart-card">{timeseries ? <TimeseriesChart series={timeseries} phases={summary.phases} band={band} /> : <p className="chart-empty">Cargando…</p>}</div>
        </div>

        <details className="technical-details" style={{ marginTop: 28 }}><summary>Ver tablas con los valores exactos</summary>
          {comparison?.available && <div className="table-scroll"><table><caption className="muted" style={{ textAlign: 'left', paddingBottom: 6 }}>{labelA} → {labelB}</caption>
            <thead><tr><th>Banda</th><th>Media {labelA}</th><th>Media {labelB}</th><th>Cambio</th><th>Cambio relativo</th></tr></thead>
            <tbody>{comparison.deltas.map(delta => <tr key={delta.band}><td>{BAND_META[delta.band].label}</td><td>{delta.mean_a?.toFixed(2) ?? '—'}</td><td>{delta.mean_b?.toFixed(2) ?? '—'}</td><td>{delta.absolute_change?.toFixed(2) ?? '—'}</td><td>{fmtPercent(delta.percent_change)}</td></tr>)}</tbody></table></div>}
          <div className="table-scroll"><table><thead><tr><th>Fase</th><th>Duración</th><th>Calidad media de señal</th><th>Datos</th></tr></thead>
            <tbody>{summary.phases.map(phase => <tr key={phase.phase_id}><td>{formatPhaseKind(phase.kind)}</td><td>{formatDuration(phase.duration_s)}</td><td>{phase.quality.mean_overall_quality == null ? '—' : phase.quality.mean_overall_quality.toFixed(0) + '%'}</td><td>{phase.sufficient ? 'Disponibles' : phase.insufficient_reason}</td></tr>)}</tbody></table></div>
          <p className="muted">{timeseries?.unit ?? 'Sin unidad disponible'} · {timeseries?.points.length ?? 0} instantes con potencia disponible.</p>
        </details>
        <div className="compare-note"><p>{comparison?.note ?? summary.note}</p></div>
      </section>

      <div className="panel no-print"><div className="section-top"><h2>Conservar una copia</h2><button className="button subtle" onClick={() => window.print()}>Imprimir</button></div>
        <div className="actions">{([['summary', 'Resumen CSV'], ['answers', 'Respuestas CSV'], ['self_reports', 'Autoevaluaciones CSV'], ['measurements', 'Mediciones CSV']] as const).map(([dataset, label]) => <a className="button subtle" key={dataset} href={api.getExportUrl(summary.session_id, dataset)} download>{label}</a>)}</div>
      </div>
    </>}
    {sessions.length > 0 && <details className="technical-details no-print"><summary>Administrar historial</summary><div className="actions">
      <button className="text-button danger" disabled={busy || selectedSessionId === null || selectedSessionId === temporarySessionId || sessions.find(session => session.id === selectedSessionId)?.status === 'ACTIVE'} onClick={() => void remove(selectedSessionId)}>Eliminar sesión seleccionada</button>
      <button className="text-button danger" disabled={busy} onClick={() => void remove(null)}>Eliminar historial finalizado</button>
    </div></details>}
  </div>;
};
