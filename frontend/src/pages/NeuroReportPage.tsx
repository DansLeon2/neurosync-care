import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { PhaseComparison, PhaseKind, SessionListItem, SessionSummary, TimeseriesOut } from '../types/neuro';
import { BAND_META, formatDuration, formatPhaseKind, formatSourceLabel } from '../utils/format';
interface Props { selectedSessionId: number | null; onSelectSessionId: (id: number | null) => void; temporarySessionId: number | null; onCloseTemporary: () => void; }
export const NeuroReportPage: React.FC<Props> = ({ selectedSessionId, onSelectSessionId, temporarySessionId, onCloseTemporary }) => {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [comparison, setComparison] = useState<PhaseComparison | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesOut | null>(null);
  const [phaseA, setPhaseA] = useState<PhaseKind>('BASELINE');
  const [phaseB, setPhaseB] = useState<PhaseKind>('REGULATION');
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
  useEffect(() => {
    let alive = true;
    setSummary(null); setComparison(null); setTimeseries(null); setError('');
    if (selectedSessionId === null) return;
    setBusy(true);
    Promise.all([api.getSessionSummary(selectedSessionId), api.comparePhases(selectedSessionId, phaseA, phaseB), api.getSessionTimeseries(selectedSessionId)])
      .then(([sum, cmp, ts]) => { if (alive) { setSummary(sum); setComparison(cmp); setTimeseries(ts); } })
      .catch(err => { if (alive) setError((err as Error).message); })
      .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [selectedSessionId, phaseA, phaseB, revision]);
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
        <div className="summary-grid"><div><span>Duración</span><strong>{formatDuration(summary.duration_s)}</strong></div><div><span>Operaciones</span><strong>{summary.math?.n_questions ?? '—'}</strong></div><div><span>Aciertos</span><strong>{summary.math?.accuracy_pct == null ? '—' : summary.math.accuracy_pct.toFixed(1) + '%'}</strong></div><div><span>Cambio de tensión percibida</span><strong>{finalChange ? (finalChange.change > 0 ? '+' : '') + finalChange.change : '—'}</strong></div></div>
        <p className="muted">Aciertos = correctas / operaciones enviadas, incluidas las omitidas. El cambio de tensión se expresa en puntos de 0 a 10, según tus respuestas.</p>
      </section>
      <section className="panel"><h2>Cómo describiste la experiencia</h2>
        {summary.self_reports.length ? <div className="report-ratings">{summary.self_reports.map((report, index) => <div key={index}><span>{report.moment === 'INITIAL' ? 'Al inicio' : report.moment === 'POST_MATH' ? 'Tras las operaciones' : report.moment === 'FINAL' ? 'Al terminar' : 'Otro momento'}</span><strong>{report.tension}<small> / 10</small></strong></div>)}</div> : <p>No se registraron autoevaluaciones.</p>}
        <p className="muted">Estos valores son percepciones personales. No se deducen del EEG.</p>
      </section>
      <details className="panel technical-details"><summary>Comparar fases y consultar datos EEG</summary>
        <div className="actions no-print">{([['Fase inicial', phaseA, setPhaseA], ['Fase de comparación', phaseB, setPhaseB]] as const).map(([label, value, setter]) => <label key={label} className="field-label">{label}<select value={value} onChange={event => setter(event.target.value as PhaseKind)}>{(['BASELINE','MATH','REGULATION'] as const).map(kind => <option key={kind} value={kind}>{formatPhaseKind(kind)}</option>)}</select></label>)}</div>
        {comparison?.available ? <div className="table-scroll"><table><thead><tr><th>Banda</th><th>Media inicial</th><th>Media comparada</th><th>Cambio</th></tr></thead><tbody>{comparison.deltas.map(delta => <tr key={delta.band}><td>{BAND_META[delta.band].label}</td><td>{delta.mean_a?.toFixed(2) ?? '—'}</td><td>{delta.mean_b?.toFixed(2) ?? '—'}</td><td>{delta.absolute_change?.toFixed(2) ?? '—'}</td></tr>)}</tbody></table></div> : <p>{comparison?.reason ?? 'Comparación no disponible.'}</p>}
        <p className="muted">{timeseries?.unit ?? 'Sin unidad disponible'} · {timeseries?.points.length ?? 0} instantes con potencia disponible. {comparison?.note}</p>
        <div className="table-scroll"><table><thead><tr><th>Fase</th><th>Duración</th><th>Datos</th></tr></thead><tbody>{summary.phases.map(phase => <tr key={phase.phase_id}><td>{formatPhaseKind(phase.kind)}</td><td>{formatDuration(phase.duration_s)}</td><td>{phase.sufficient ? 'Disponibles' : phase.insufficient_reason}</td></tr>)}</tbody></table></div>
      </details>
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
