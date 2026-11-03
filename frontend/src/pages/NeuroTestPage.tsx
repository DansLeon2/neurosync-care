import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import type { CognitiveAnswerOut, MathAnswerOut, MathDifficulty, MathQuestionOut, ProtocolOut, SessionOut } from '../types/neuro';
import { formatDuration } from '../utils/format';

interface Props {
  activeSession: SessionOut | null;
  protocol: ProtocolOut;
  onComplete?: () => Promise<void>;
}
export const NeuroTestPage: React.FC<Props> = ({ activeSession, protocol, onComplete }) => {
  const phase = activeSession?.phases.find(p => p.kind === 'MATH' && p.status === 'ACTIVE');
  const [difficulty, setDifficulty] = useState<MathDifficulty>(phase?.detail === 'MEDIUM' || phase?.detail === 'HARD' ? phase.detail : 'EASY');
  const [question, setQuestion] = useState<MathQuestionOut | null>(null);
  const [input, setInput] = useState('');
  const [answers, setAnswers] = useState<(MathAnswerOut | CognitiveAnswerOut)[]>([]);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const [practiceStart, setPracticeStart] = useState<number | null>(null);
  const [done, setDone] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const generation = useRef(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const mathDef = protocol.phases.find(p => p.kind === 'MATH')!;
  const roundDeadline = phase ? Date.parse(phase.started_at) + (phase.planned_duration_s ?? mathDef.default_duration_s) * 1000
    : practiceStart ? practiceStart + mathDef.default_duration_s * 1000 : null;
  const running = !done && (Boolean(phase) || practiceStart !== null);
  const expired = roundDeadline !== null && now >= roundDeadline;
  const limit = protocol.math.max_questions;
  const answered = answers.filter(answer => answer.result !== 'SKIPPED');
  const correct = answers.filter(answer => answer.result === 'CORRECT').length;
  const canAnswer = running && !expired && !busy && question !== null;

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!activeSession || !phase) return;
    let alive = true;
    api.getSessionDetail(activeSession.id).then(detail => {
      if (alive) setAnswers(previous => { const saved = detail.answers.filter(answer => answer.phase_id === phase.id); return [...saved, ...previous.filter(answer => !saved.some(item => item.question_id === answer.question_id))]; });
    }).catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, [activeSession?.id, phase?.id]);

  const next = useCallback(async () => {
    const requestId = ++generation.current;
    const value = await api.issueMathQuestion(difficulty, phase ? activeSession!.id : null);
    if (requestId === generation.current) { setQuestion(value); setInput(''); }
  }, [difficulty, activeSession?.id, phase?.id]);

  useEffect(() => {
    if (!running || expired) return;
    let alive = true;
    setBusy(true);
    next().catch(err => { if (alive) setError((err as Error).message); })
      .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; generation.current++; };
  }, [next, running]);

  const finish = useCallback(async () => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    generation.current++;
    setQuestion(null);
    try { if (onComplete) await onComplete(); setDone(true); setPracticeStart(null); }
    catch (err) { setError((err as Error).message); }
    finally { lock.current = false; setBusy(false); }
  }, [onComplete]);

  useEffect(() => {
    if (running && (expired || answers.length >= limit) && !busy && !error) void finish();
  }, [running, expired, answers.length, limit, busy, error, finish]);

  useEffect(() => { if (canAnswer) inputRef.current?.focus(); }, [canAnswer, question?.question_id]);

  const submit = async (skip: boolean) => {
    if (!canAnswer || lock.current || (!skip && !/^-?\d{1,4}$/.test(input))) return;
    if (roundDeadline !== null && Date.now() >= roundDeadline) { setNow(Date.now()); return; }
    lock.current = true; setBusy(true); setError('');
    let reachedLimit = false;
    try {
      const result = await api.submitMathAnswer(question!.question_id, skip ? null : Number(input));
      setAnswers(previous => [...previous, result]);
      setFeedback(result.result === 'CORRECT' ? 'Correcto.' : result.result === 'SKIPPED'
        ? `Omitida. Respuesta: ${result.expected_answer}.` : `Respuesta correcta: ${result.expected_answer}.`);
      setQuestion(null); setInput('');
      reachedLimit = answers.length + 1 >= limit || (phase && question!.question_number >= limit) || false;
      if (!reachedLimit && (roundDeadline === null || Date.now() < roundDeadline)) await next();
    } catch (err) { setError((err as Error).message); }
    finally { lock.current = false; setBusy(false); }
    if (reachedLimit) await finish();
  };

  const retry = async () => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try {
      if (phase && activeSession) {
        const detail = await api.getSessionDetail(activeSession.id);
        setAnswers(detail.answers.filter(answer => answer.phase_id === phase.id));
      }
      if (!expired) await next();
    } catch (err) { setError((err as Error).message); }
    finally { lock.current = false; setBusy(false); }
  };

  return <section className="panel math-panel">
    <div className="section-top"><div><span className="eyebrow">{phase ? 'Actividad de la sesión' : 'Práctica sin guardar'}</span>
      <h2>Una operación a la vez</h2></div>
      {running && <span className="timer" role="timer" aria-label="Tiempo restante">{formatDuration(Math.ceil(Math.max(0, (roundDeadline! - now) / 1000)))}</span>}
    </div>
    <p>Hasta {limit} operaciones o {formatDuration(phase?.planned_duration_s ?? mathDef.default_duration_s)}. Puedes omitir una respuesta o terminar cuando quieras.</p>
    {!running && !phase && !done && <div className="actions">
      <label>Dificultad <select value={difficulty} onChange={event => setDifficulty(event.target.value as MathDifficulty)}>
        <option value="EASY">Fácil</option><option value="MEDIUM">Media</option><option value="HARD">Alta</option>
      </select></label>
      <button className="button primary" disabled={Boolean(activeSession)} onClick={() => { setAnswers([]); setDone(false); setPracticeStart(Date.now()); }}>Comenzar práctica</button>
      {activeSession && <p>Continúa tu actividad desde Mi sesión.</p>}
    </div>}
    {running && <form className="arithmetic" onSubmit={event => { event.preventDefault(); void submit(false); }}>
      <span className="eyebrow">Operación {question?.question_number && phase ? question.question_number : Math.min(answers.length + 1, limit)} de {limit}</span>
      <div className="equation">{expired ? 'Tiempo cumplido' : question?.text ?? (busy ? 'Preparando…' : 'Sin operación pendiente')}</div>
      <label className="answer-label" htmlFor="math-answer">Tu respuesta</label>
      <input id="math-answer" ref={inputRef} className="answer-input" type="text" inputMode="numeric"
        autoComplete="off" value={input} disabled={!canAnswer} maxLength={5}
        onChange={event => { if (/^-?\d{0,4}$/.test(event.target.value)) setInput(event.target.value); }} />
      <p className="muted">Enter para confirmar · Hasta cuatro cifras</p>
      <details className="keypad-details"><summary>Mostrar teclado en pantalla</summary><div className="keypad">
        {['7','8','9','4','5','6','1','2','3','−','0','⌫'].map(key => <button type="button" key={key} disabled={!canAnswer}
          onClick={() => setInput(value => key === '⌫' ? value.slice(0, -1) : key === '−' ? (value.startsWith('-') ? value.slice(1) : '-' + value) : value.replace('-', '').length < 4 ? value + key : value)}>{key}</button>)}
      </div></details>
      <div className="actions centered">
        <button className="button primary" disabled={!canAnswer || !/^-?\d{1,4}$/.test(input)}>Confirmar</button>
        <button type="button" className="button subtle" disabled={!canAnswer} onClick={() => void submit(true)}>Omitir</button>
      </div>
    </form>}
    <p className="feedback" role="status">{feedback}</p>
    {error && <div role="alert" className="error-message">{error}<button className="text-button" onClick={() => void retry()} disabled={busy}>Reintentar</button></div>}
    {done && <div className="empty-state"><h3>Actividad terminada</h3><p>{answers.length} operaciones · {correct} correctas · {answers.filter(a => a.result === 'SKIPPED').length} omitidas.</p>
      {!activeSession && <button className="button subtle" onClick={() => { setDone(false); setAnswers([]); setFeedback(''); setError(''); }}>Volver a practicar</button>}</div>}
    {(running || done) && <details className="technical-details"><summary>Ver resumen de respuestas</summary>
      <p>{answers.length} operaciones · {correct} correctas · {answers.length ? (100 * correct / answers.length).toFixed(1) + '%' : '—'} de aciertos (incluye omisiones).</p>
      <p>Tiempo medio: {answered.length ? Math.round(answered.reduce((sum, answer) => sum + answer.response_time_ms, 0) / answered.length) + ' ms' : '—'}.</p>
    </details>}
    {running && <button className="text-button" disabled={busy} onClick={() => void finish()}>{expired ? 'Continuar' : 'Terminar actividad'}</button>}
  </section>;
};
