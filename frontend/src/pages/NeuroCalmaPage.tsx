import React, { useEffect, useRef, useState } from 'react';
import type { ProtocolOut, SessionOut } from '../types/neuro';
import { formatDuration } from '../utils/format';
interface Props { activeSession: SessionOut | null; protocol: ProtocolOut; onComplete?: () => Promise<void>; }
const techniques = [
  { id: 'BREATH_4_6', label: 'Respiración suave', description: 'Inhala 4 segundos y exhala 6, solo si te resulta cómodo.', inhale: 4, exhale: 6 },
  { id: 'BREATH_4_4', label: 'Respiración equilibrada', description: 'Inhala 4 segundos y exhala 4, sin retener el aire.', inhale: 4, exhale: 4 },
  { id: 'OPEN_ATTENTION', label: 'Atención al entorno', description: 'Observa los colores y escucha los sonidos, respirando a tu ritmo.', inhale: 0, exhale: 0 },
];
const prompts = ['Observa tres colores a tu alrededor.', 'Siente el apoyo de tus pies.', 'Escucha los sonidos del entorno.', 'Deja descansar tus hombros.'];
export const NeuroCalmaPage: React.FC<Props> = ({ activeSession, protocol, onComplete }) => {
  const phase = activeSession?.phases.find(p => p.kind === 'REGULATION' && p.status === 'ACTIVE');
  const definition = protocol.phases.find(p => p.kind === 'REGULATION')!;
  const duration = phase?.planned_duration_s ?? definition.default_duration_s;
  const [techniqueIndex, setTechniqueIndex] = useState(0);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lastTick = useRef(Date.now());
  const lock = useRef(false);
  const technique = techniques[techniqueIndex];
  useEffect(() => {
    setElapsed(phase ? Math.min(duration, Math.max(0, (Date.now() - Date.parse(phase.started_at)) / 1000)) : 0);
    setRunning(Boolean(phase)); setDone(false);
  }, [phase?.id]);
  useEffect(() => {
    if (!running) return;
    lastTick.current = Date.now();
    const timer = window.setInterval(() => {
      const now = Date.now();
      setElapsed(value => Math.min(duration, value + (now - lastTick.current) / 1000));
      lastTick.current = now;
    }, 250);
    return () => window.clearInterval(timer);
  }, [running, duration]);
  const complete = async () => {
    if (lock.current) return;
    lock.current = true; setRunning(false); setBusy(true); setError('');
    try { if (onComplete) await onComplete(); setDone(true); }
    catch (err) { setError((err as Error).message); }
    finally { lock.current = false; setBusy(false); }
  };
  useEffect(() => { if (elapsed >= duration && !done && !busy && !error) void complete(); }, [elapsed, duration, done, busy, error]);
  const cycle = technique.inhale + technique.exhale;
  const inhale = cycle > 0 && elapsed % cycle < technique.inhale;
  const label = technique.id === 'OPEN_ATTENTION' ? prompts[Math.floor(elapsed / 12) % prompts.length] : inhale ? 'Inhala suavemente' : 'Exhala sin esfuerzo';
  return <section className="panel exercise-panel">
    <span className="eyebrow">{phase ? 'Calma de la sesión' : 'Práctica sin guardar'}</span><h2>Un momento para ti</h2>
    <p>Respira con comodidad. Puedes pausar la guía o terminar en cualquier momento.</p>
    <label className="field-label">Elige una guía<select value={techniqueIndex} disabled={running || busy} onChange={event => setTechniqueIndex(Number(event.target.value))}>
      {techniques.map((value, index) => <option key={value.id} value={index}>{value.label}</option>)}
    </select></label>
    <p>{technique.description}</p>
    <div className={`breath-orb ${running && inhale ? 'inhale' : ''}`} aria-hidden="true"><span /></div>
    <p className="breath-prompt" role="status">{done ? 'Ejercicio terminado' : running ? label : 'A tu propio ritmo'}</p>
    <span className="timer">{formatDuration(Math.ceil(Math.max(0, duration - elapsed)))}</span>
    {phase && !running && !done && <p className="muted">La guía está pausada; el registro EEG de esta fase continúa.</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
    <div className="actions centered">
      {!done && <button className="button primary" disabled={busy || elapsed >= duration || Boolean(activeSession && !phase)}
        onClick={() => { setRunning(!running); setError(''); }}>{running ? 'Pausar guía' : elapsed > 0 ? 'Continuar guía' : 'Comenzar'}</button>}
      {!done && (phase || elapsed > 0) && <button className="button subtle" disabled={busy} onClick={() => void complete()}>Terminar y continuar</button>}
      {done && !activeSession && <button className="button subtle" onClick={() => { setElapsed(0); setDone(false); }}>Volver a practicar</button>}
    </div>
    {activeSession && !phase && <p>Continúa tu actividad desde Mi sesión.</p>}
  </section>;
};
