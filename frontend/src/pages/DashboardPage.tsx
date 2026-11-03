import React, { useCallback, useEffect, useState } from 'react';
import { ArrowRight, Check, Leaf, Play } from 'lucide-react';
import { api } from '../services/api';
import { SelfReportForm } from '../components/SelfReportForm';
import { NeuroTestPage } from './NeuroTestPage';
import { NeuroCalmaPage } from './NeuroCalmaPage';
import type { HistoryPoint, LogEntry } from '../hooks/useNeuroStream';
import type { MathDifficulty, NavTab, PhaseKind, ProtocolOut, RealtimeFrame, SessionDetail, SessionOut, SourceStatus } from '../types/neuro';
import { BAND_META, computeBandAverage, formatDuration, formatSourceLabel } from '../utils/format';

interface Props {
  status: SourceStatus; frame: RealtimeFrame | null; history: HistoryPoint[]; logs: LogEntry[];
  activeSession: SessionOut | null; protocol: ProtocolOut;
  onNavigate: (tab: NavTab) => void; onOpenStartSession: () => void;
  onRefreshState: () => Promise<void>; onFinish: () => Promise<void>;
}
export const DashboardPage: React.FC<Props> = ({ status, frame, history, logs, activeSession, protocol, onNavigate, onOpenStartSession, onRefreshState, onFinish }) => {
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [difficulty, setDifficulty] = useState<MathDifficulty>('EASY');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [now, setNow] = useState(Date.now());
  const phase = activeSession?.phases.find(value => value.status === 'ACTIVE');
  const completed = (kind: PhaseKind) => activeSession?.phases.some(value => value.kind === kind && value.status === 'COMPLETED');
  const signature = activeSession?.phases.map(value => value.id + value.status).join(',');
  const loadDetail = useCallback(async () => {
    if (activeSession) setDetail(await api.getSessionDetail(activeSession.id));
    else setDetail(null);
  }, [activeSession?.id]);
  useEffect(() => {
    let alive = true;
    if (!activeSession) { setDetail(null); return; }
    api.getSessionDetail(activeSession.id).then(value => { if (alive) setDetail(value); })
      .catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, [activeSession?.id, signature]);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, []);
  const action = async (work: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); setError('');
    try { await work(); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  const start = async (kind: PhaseKind) => {
    if (!activeSession) return;
    await api.startPhase(activeSession.id, kind, undefined, kind === 'MATH' ? difficulty : undefined);
    await onRefreshState();
  };
  const end = useCallback(async () => {
    if (!activeSession || !phase) return;
    await api.endPhase(activeSession.id, phase.id);
    await onRefreshState();
  }, [activeSession?.id, phase?.id, onRefreshState]);
  const baselineDef = protocol.phases.find(value => value.kind === 'BASELINE')!;
  const baselineRemaining = phase?.kind === 'BASELINE'
    ? Math.max(0, Math.ceil((Date.parse(phase.started_at) + (phase.planned_duration_s ?? baselineDef.default_duration_s) * 1000 - now) / 1000)) : null;
  useEffect(() => {
    if (baselineRemaining === 0 && !busy && !error) void action(end);
  }, [baselineRemaining, busy, error, end]);
  const hasReport = (moment: string) => detail?.self_reports.some(report => report.moment === moment);
  const step = !activeSession || !completed('BASELINE') ? 0 : !completed('MATH') || !hasReport('POST_MATH') ? 1 : 2;
  const total = protocol.phases.reduce((sum, value) => sum + value.default_duration_s, 0);
  const chart = history.slice(-120);
  const valid = chart.map(value => value.bands.alpha).filter((value): value is number => value !== null && Number.isFinite(value));
  const min = Math.min(...valid), max = Math.max(...valid);
  let connected = false;
  let path = '';
  chart.forEach((point, index) => {
    const value = point.bands.alpha;
    if (value === null || !Number.isFinite(value)) { connected = false; return; }
    if (index > 0 && Date.parse(point.timestamp) - Date.parse(chart[index - 1].timestamp) > 500) connected = false;
    const x = index / Math.max(1, chart.length - 1) * 700;
    const y = 90 - ((value - min) / Math.max(1, max - min)) * 70;
    path += `${connected ? ' L' : ' M'}${x.toFixed(1)},${y.toFixed(1)}`; connected = true;
  });
  return <div className="workspace">
    <div className="page-title"><span className="eyebrow">Mi sesión</span><h1>Un paso a la vez.</h1><p>Observa tu punto de partida, practica y toma una pausa.</p></div>
    <ol className="session-steps" aria-label="Progreso de la sesión">
      {['Preparar', 'Actividad', 'Calma', 'Resultados'].map((label, index) => <li key={label} className={index === step ? 'current' : index < step ? 'complete' : ''} aria-current={index === step ? 'step' : undefined}>
        <span>{index < step ? <Check size={15} /> : index + 1}</span><strong>{label}</strong>
      </li>)}
    </ol>
    {error && <div className="error-message" role="alert">{error}<button className="text-button" onClick={() => void action(async () => { await loadDetail(); await onRefreshState(); })}>Reintentar</button></div>}
    {!activeSession ? <section className="panel welcome-panel">
      <div className="welcome-copy"><span className="pill"><Leaf size={14} /> Un espacio para observarte</span>
        <h2>Conoce tu actividad.<br />Encuentra tu ritmo.</h2>
        <p>Una sesión guiada de unos {Math.round(total / 60)} minutos. Funciona con un simulador o con tu dispositivo EEG.</p>
        <button className="button primary" onClick={onOpenStartSession}><Play size={16} /> Preparar mi sesión <ArrowRight size={17} /></button>
        <small>Podrás elegir si guardar tus resultados.</small>
      </div><div className="welcome-art" aria-hidden="true"><div /><div /><div /><Leaf size={64} strokeWidth={1} /></div>
    </section> : <>
      <div className="session-meta"><span>Sesión #{activeSession.id} · {activeSession.test_mode ? 'Demostración rápida' : 'Duración estándar'}</span><span>{activeSession.consent_storage ? 'Se guardará en tu historial local' : 'Sesión temporal'}</span></div>
      {phase?.kind === 'BASELINE' ? <section className="panel exercise-panel">
        <span className="eyebrow">Preparar · Referencia inicial</span><h2>Comienza con una pausa.</h2><p>Siéntate cómodamente y permanece en reposo. La siguiente actividad estará lista al terminar.</p>
        <div className="rest-symbol" aria-hidden="true"><Leaf size={48} strokeWidth={1.2} /></div>
        <span className="timer" role="timer" aria-label="Tiempo de referencia restante">{formatDuration(baselineRemaining)}</span><p className="muted">Puedes detener la sesión desde el botón superior.</p>
        {baselineRemaining === 0 && <button className="button primary" disabled={busy} onClick={() => void action(end)}>Continuar</button>}
      </section> : phase?.kind === 'MATH' ? <NeuroTestPage key={phase.id} activeSession={activeSession} protocol={protocol} onComplete={end} />
        : phase?.kind === 'REGULATION' ? <NeuroCalmaPage key={phase.id} activeSession={activeSession} protocol={protocol} onComplete={end} />
        : !detail || detail.session.id !== activeSession.id ? <section className="panel"><p role="status">Recuperando tu progreso…</p></section>
        : !completed('BASELINE') ? <section className="panel"><h2>Preparar la referencia</h2><button className="button primary" disabled={busy} onClick={() => void action(() => start('BASELINE'))}>Comenzar referencia</button></section>
        : !completed('MATH') ? <section className="panel exercise-panel"><span className="eyebrow">Actividad</span><h2>Continúa con operaciones sencillas.</h2><p>Hasta {protocol.math.max_questions} operaciones. Responde a tu ritmo; puedes omitir o terminar antes.</p>
          <label className="field-label">Dificultad<select value={difficulty} onChange={event => setDifficulty(event.target.value as MathDifficulty)}><option value="EASY">Fácil</option><option value="MEDIUM">Media</option><option value="HARD">Alta</option></select></label><button className="button primary" disabled={busy} onClick={() => void action(() => start('MATH'))}>Comenzar operaciones <ArrowRight size={17} /></button></section>
        : !hasReport('POST_MATH') ? <SelfReportForm key="post-math" moment="POST_MATH" onSave={async tension => {
          await api.addSelfReport(activeSession.id, { moment: 'POST_MATH', tension, phase_id: activeSession.phases.find(p => p.kind === 'MATH')?.id });
          await loadDetail();
        }} />
        : !completed('REGULATION') ? <section className="panel exercise-panel"><span className="eyebrow">Calma</span><h2>Ahora, baja el ritmo.</h2><p>Elige una guía de respiración suave o presta atención al entorno.</p>
          <button className="button primary" disabled={busy} onClick={() => void action(() => start('REGULATION'))}>Comenzar pausa <ArrowRight size={17} /></button></section>
        : <SelfReportForm key="final" moment="FINAL" onSave={async tension => {
          if (!hasReport('FINAL')) await api.addSelfReport(activeSession.id, { moment: 'FINAL', tension, phase_id: activeSession.phases.find(p => p.kind === 'REGULATION')?.id });
          await loadDetail(); await onFinish();
        }} />}
    </>}
    <div className="support-row"><div><span className="status-dot" data-online={status.connection === 'STREAMING'} />{formatSourceLabel(status.source)}</div>
      <button className="text-button" onClick={() => onNavigate('hardware')}>Revisar dispositivo <ArrowRight size={14} /></button></div>
    {status.connection !== 'STREAMING' && activeSession && <p className="error-message" role="status">No hay señal disponible. El tiempo de la actividad continúa; puedes detener la sesión y revisar el dispositivo.</p>}
    <details className="panel technical-details"><summary>Ver telemetría y detalles técnicos</summary>
      <p>Potencia por banda · {frame?.pow_unit ?? 'Unidad no disponible'}. Esta gráfica muestra valores recibidos; no es EEG crudo.</p>
      <div className="band-values">{(['theta', 'alpha', 'low_beta', 'high_beta', 'gamma'] as const).map(band => <div key={band}><span>{BAND_META[band].label}</span><strong>{computeBandAverage(frame, band)?.toFixed(2) ?? '—'}</strong></div>)}</div>
      {valid.length > 1 ? <figure><svg viewBox="0 0 700 110" role="img" aria-label="Potencia alfa media de los últimos datos recibidos"><path d={path} fill="none" stroke="currentColor" strokeWidth="2" /></svg><figcaption>Alfa media · escala automática · interrupciones sin interpolación</figcaption></figure> : <p>Esperando suficientes muestras para mostrar la gráfica.</p>}
      <details><summary>Bitácora de conexión</summary><ul className="log-list">{logs.slice(-10).map(log => <li key={log.id}>{log.time} · {log.text}</li>)}</ul></details>
    </details>
  </div>;
};
