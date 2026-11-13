import React, { useState } from 'react';
import type { ReportMoment, SelfReportExtras } from '../types/neuro';
export function SelfReportForm({ moment, onSave }: { moment: ReportMoment; onSave: (tension: number, extras: SelfReportExtras) => Promise<void> }) {
  const [tension, setTension] = useState<number | null>(null);
  const [extras, setExtras] = useState({ difficulty: '', effort: '', comfort: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lock = React.useRef(false);
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); if (lock.current || tension === null) return;
    lock.current = true; setBusy(true); setError('');
    try { await onSave(tension, {
      difficulty: extras.difficulty === '' ? null : Number(extras.difficulty),
      effort: extras.effort === '' ? null : Number(extras.effort),
      comfort: extras.comfort === '' ? null : Number(extras.comfort),
    }); } catch (err) { setError((err as Error).message); } finally { lock.current = false; setBusy(false); }
  };
  return <section className="panel exercise-panel"><form onSubmit={event => void save(event)}>
    <span className="eyebrow">{moment === 'FINAL' ? 'Antes de ver tus resultados' : 'Una pausa para observar'}</span>
    <h2>¿Cuánta tensión percibes ahora?</h2><p>Elige un número del 0 al 10. Esta respuesta describe cómo te sientes.</p>
    <div className="rating" role="group" aria-label="Tensión percibida de 0 a 10">
      {Array.from({ length: 11 }, (_, value) => <button type="button" key={value} aria-pressed={tension === value} className={tension === value ? 'selected' : ''} onClick={() => setTension(value)}>{value}</button>)}
    </div><div className="rating-labels"><span>Sin tensión</span><span>Máxima tensión</span></div>
    <details className="subjective-extras"><summary>Añadir dificultad, esfuerzo y comodidad (opcional)</summary>
      <div className="explorer-filters">{([['difficulty','Dificultad percibida'],['effort','Esfuerzo percibido'],['comfort','Comodidad']] as const).map(([key,label]) => <label className="field-label" key={key}>{label} · 0–10<input type="number" min="0" max="10" step="1" value={extras[key]} onChange={event => setExtras(values => ({ ...values, [key]: event.target.value }))} /></label>)}</div>
      <p className="muted">Deja vacío lo que no quieras responder. Estas percepciones se guardan por separado del EEG.</p>
    </details>
    {error && <p className="error-message" role="alert">{error}</p>}
    <div className="actions"><button className="button primary" disabled={busy || tension === null}>Guardar y continuar</button></div>
  </form></section>;
}
