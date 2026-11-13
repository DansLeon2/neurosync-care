import React, { useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';
import type { CodingAnswer, CodingTask, PhaseOut, SessionOut } from '../../types/neuro';
import { formatDuration } from '../../utils/format';

export function CodingActivity({ session, phase, task, onComplete }: { session: SessionOut; phase: PhaseOut; task: CodingTask | undefined; onComplete: () => Promise<void> }) {
  const [choice, setChoice] = useState<number | null>(null);
  const [answers, setAnswers] = useState<CodingAnswer[]>([]);
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lock = useRef(false);
  const deadline = Date.parse(phase.started_at) + (phase.planned_duration_s ?? 120) * 1000;
  const expired = now >= deadline;
  const solved = answers.some(answer => answer.correct);
  const finished = solved || answers.length >= (task?.max_attempts ?? 3);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(timer); }, []);
  useEffect(() => {
    let alive = true;
    api.getSessionDetail(session.id).then(detail => { if (alive) setAnswers(detail.coding_answers.filter(answer => answer.phase_id === phase.id)); }).catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, [session.id, phase.id]);
  const complete = async () => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try { await onComplete(); } catch (err) { setError((err as Error).message); } finally { lock.current = false; setBusy(false); }
  };
  useEffect(() => { if (expired && !busy && !error) void complete(); }, [expired, busy, error]);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); if (!task || choice === null || lock.current || expired || finished) return;
    lock.current = true; setBusy(true); setError('');
    try { const answer = await api.submitCodingAnswer(session.id, task.id, choice); setAnswers(previous => [...previous, answer]); setChoice(null); }
    catch (err) { setError((err as Error).message); } finally { lock.current = false; setBusy(false); }
  };
  return <section className="panel coding-activity">
    <div className="section-top"><div><span className="eyebrow">NeuroCode · piloto controlado</span><h2>{task?.title ?? 'Recuperando tarea…'}</h2></div><span className="timer" role="timer">{formatDuration(Math.ceil(Math.max(0, deadline-now)/1000))}</span></div>
    {task && <><p>{task.prompt}</p><pre className="code-snippet"><code>{task.code}</code></pre>
      <form onSubmit={event => void submit(event)}><fieldset disabled={busy || expired || finished}><legend>Selecciona una respuesta</legend><div className="code-options">{task.options.map((option,index) => <label key={index}><input type="radio" name="coding-choice" checked={choice === index} onChange={() => setChoice(index)} />{option}</label>)}</div></fieldset>
        <div className="actions"><button className="button primary" disabled={busy || choice === null || expired || finished}>Enviar respuesta</button><button type="button" className="button subtle" disabled={busy} onClick={() => void complete()}>Terminar tarea</button></div>
      </form><p className="muted">{task.criteria} Máximo {task.max_attempts} intentos. El tiempo se cuenta desde el inicio de la fase.</p>
      <p role="status" className="coding-feedback">{solved ? 'Respuesta correcta. Puedes continuar a la autoevaluación.' : answers.length ? `${answers.length} intento(s) registrado(s). ${finished ? 'Se alcanzó el límite.' : 'La respuesta no fue correcta; puedes intentarlo de nuevo.'}` : 'Todavía no has enviado respuestas.'}</p>
    </>}
    {error && <p role="alert" className="error-message">{error}<button className="text-button" disabled={busy} onClick={() => void complete()}>Continuar a la autoevaluación</button></p>}
    {!task && <button className="button subtle" disabled={busy} onClick={() => void complete()}>Terminar tarea sin respuesta</button>}
  </section>;
}
