import React, { useEffect, useState } from 'react';
import { ArrowRight, Check, Leaf, Play } from 'lucide-react';
import { api } from '../services/api';
import { SelfReportForm } from '../components/SelfReportForm';
import { NeuroTestPage } from './NeuroTestPage';
import { NeuroCalmaPage } from './NeuroCalmaPage';
import { CodingActivity } from '../features/neurocode/CodingActivity';
import { LiveTelemetryPanel } from '../features/telemetry/LiveTelemetryPanel';
import { useGuidedSession } from '../features/session/useGuidedSession';
import type { LogEntry } from '../hooks/useNeuroStream';
import type { CodingTask, MathDifficulty, NavTab, ProtocolOut, SensorLayout, SessionOut, SourceStatus } from '../types/neuro';
import { formatDuration } from '../utils/format';

interface Props {
  status: SourceStatus; layout: SensorLayout | null; logs: LogEntry[];
  activeSession: SessionOut | null; protocol: ProtocolOut;
  onNavigate: (tab: NavTab) => void; onOpenStartSession: () => void;
  onRefreshState: () => Promise<void>; onFinish: () => Promise<void>;
}
export const DashboardPage: React.FC<Props> = ({ status, layout, logs, activeSession, protocol, onNavigate, onOpenStartSession, onRefreshState, onFinish }) => {
  const flow = useGuidedSession(activeSession, protocol, onRefreshState);
  const { detail, busy, error, action, phase, baselineRemaining, completed, hasReport, loadDetail, start, end } = flow;
  const [difficulty, setDifficulty] = useState<MathDifficulty>('EASY');
  const [tasks, setTasks] = useState<CodingTask[]>([]);
  const [taskId, setTaskId] = useState('');
  const [taskError, setTaskError] = useState('');
  const [catalogRequest, setCatalogRequest] = useState(0);
  const coding = activeSession?.activity_kind === 'CODING';
  useEffect(() => {
    if (!coding) return;
    let alive = true;
    setTaskError('');
    api.getCodingTasks().then(values => { if (alive) { setTasks(values); setTaskId(values[0]?.id ?? ''); } }).catch(err => { if (alive) setTaskError((err as Error).message); });
    return () => { alive = false; };
  }, [coding, activeSession?.id, catalogRequest]);
  const kind = coding ? 'CODING' : 'MATH';
  const moment = coding ? 'POST_CODING' : 'POST_MATH';
  const step = !activeSession || !completed('BASELINE') ? 0 : !completed(kind) || !hasReport(moment) ? 1 : 2;
  const total = protocol.phases.reduce((sum, value) => sum + value.default_duration_s, 0);
  const telemetry = <LiveTelemetryPanel status={status} layout={layout} logs={logs} onExplore={() => onNavigate('neuromap')} />;
  return <div className="workspace session-workspace">
    <div className="page-title"><span className="eyebrow">Mi sesión</span><h1>Un paso a la vez.</h1><p>Observa tu punto de partida, practica y toma una pausa.</p></div>
    <ol className="session-steps" aria-label="Progreso de la sesión">
      {['Preparar', 'Actividad', 'Calma', 'Resultados'].map((label,index) => <li key={label} className={index === step ? 'current' : index < step ? 'complete' : ''} aria-current={index === step ? 'step' : undefined}><span>{index < step ? <Check size={15} /> : index+1}</span><strong>{label}</strong></li>)}
    </ol>
    {error && <div className="error-message" role="alert">{error}<button className="text-button" onClick={() => void action(async () => { await loadDetail(); await onRefreshState(); })}>Reintentar</button></div>}
    {coding && taskError && <div className="error-message" role="alert">{taskError}<button className="text-button" onClick={() => setCatalogRequest(value => value + 1)}>Reintentar catálogo de tareas</button></div>}
    {!activeSession ? <>
      <section className="panel welcome-panel"><div className="welcome-copy"><span className="pill"><Leaf size={14} /> Un espacio para observarte</span><h2>Conoce tu actividad.<br />Encuentra tu ritmo.</h2><p>Una sesión guiada de unos {Math.round(total/60)} minutos. Funciona con un simulador o con tu dispositivo EEG.</p><button className="button primary" onClick={onOpenStartSession}><Play size={16} /> Preparar mi sesión <ArrowRight size={17} /></button><small>Podrás elegir si guardar tus resultados.</small></div><div className="welcome-art" aria-hidden="true"><div /><div /><div /><Leaf size={64} strokeWidth={1} /></div></section>
      {telemetry}
    </> : <>
      <div className="session-meta"><span>Sesión #{activeSession.id} · {activeSession.test_mode ? 'Demostración rápida' : 'Duración estándar'} · {coding ? 'Lectura de código' : 'Operaciones'}</span><span>{activeSession.consent_storage ? 'Se guardará en tu historial local' : 'Sesión temporal'}</span></div>
      <div className="experience-grid"><div className="experience-task">
      {phase?.kind === 'BASELINE' ? <section className="panel exercise-panel"><span className="eyebrow">Preparar · Referencia inicial</span><h2>Comienza con una pausa.</h2><p>Siéntate cómodamente y permanece en reposo. La siguiente actividad estará lista al terminar.</p><div className="rest-symbol" aria-hidden="true"><Leaf size={48} strokeWidth={1.2} /></div><span className="timer" role="timer" aria-label="Tiempo de referencia restante">{formatDuration(baselineRemaining)}</span><p className="muted">Puedes detener la sesión desde el botón superior.</p>{baselineRemaining === 0 && <button className="button primary" disabled={busy} onClick={() => void action(end)}>Continuar</button>}</section>
        : phase?.kind === 'MATH' ? <NeuroTestPage key={phase.id} activeSession={activeSession} protocol={protocol} onComplete={end} />
        : phase?.kind === 'CODING' ? <CodingActivity key={phase.id} session={activeSession} phase={phase} task={tasks.find(task => task.id === phase.detail)} onComplete={end} />
        : phase?.kind === 'REGULATION' ? <NeuroCalmaPage key={phase.id} activeSession={activeSession} protocol={protocol} onComplete={end} />
        : !detail || detail.session.id !== activeSession.id ? <section className="panel"><p role="status">Recuperando tu progreso…</p></section>
        : !completed('BASELINE') ? <section className="panel"><h2>Preparar la referencia</h2><button className="button primary" disabled={busy} onClick={() => void action(() => start('BASELINE'))}>Comenzar referencia</button></section>
        : !completed(kind) ? <section className="panel exercise-panel"><span className="eyebrow">Actividad</span><h2>{coding ? 'Explora un fragmento de código.' : 'Continúa con operaciones sencillas.'}</h2><p>{coding ? 'Lee una tarea controlada y selecciona una respuesta. Se registran intentos y tiempos, sin ejecutar código.' : `Hasta ${protocol.math.max_questions} operaciones. Responde a tu ritmo; puedes omitir o terminar antes.`}</p>
          {coding ? <label className="field-label">Tarea<select value={taskId} onChange={event => setTaskId(event.target.value)}>{tasks.map(task => <option key={task.id} value={task.id}>{task.title} · {task.difficulty}</option>)}</select></label>
            : <label className="field-label">Dificultad<select value={difficulty} onChange={event => setDifficulty(event.target.value as MathDifficulty)}><option value="EASY">Fácil</option><option value="MEDIUM">Media</option><option value="HARD">Alta</option></select></label>}
          <button className="button primary" disabled={busy || coding && !taskId} onClick={() => void action(() => start(kind, coding ? taskId : difficulty))}>{coding ? 'Comenzar lectura de código' : 'Comenzar operaciones'} <ArrowRight size={17} /></button></section>
        : !hasReport(moment) ? <SelfReportForm key={moment} moment={moment} onSave={async (tension,extras) => { await api.addSelfReport(activeSession.id, { moment, tension, ...extras, phase_id: [...activeSession.phases].reverse().find(value => value.kind === kind)?.id }); await loadDetail(); }} />
        : !completed('REGULATION') ? <section className="panel exercise-panel"><span className="eyebrow">Calma</span><h2>Ahora, baja el ritmo.</h2><p>Elige una guía de respiración suave o presta atención al entorno.</p><button className="button primary" disabled={busy} onClick={() => void action(() => start('REGULATION'))}>Comenzar pausa <ArrowRight size={17} /></button></section>
        : <SelfReportForm key="final" moment="FINAL" onSave={async (tension,extras) => { if (!hasReport('FINAL')) await api.addSelfReport(activeSession.id, { moment: 'FINAL', tension, ...extras, phase_id: [...activeSession.phases].reverse().find(value => value.kind === 'REGULATION')?.id }); await loadDetail(); await onFinish(); }} />}
      </div><aside className="experience-observer">{telemetry}</aside></div>
    </>}
  </div>;
};
