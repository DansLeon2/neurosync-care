import React, { useState } from 'react';
import type { ReportMoment } from '../types/neuro';
export function SelfReportForm({ moment, onSave }: { moment: ReportMoment; onSave: (tension: number) => Promise<void> }) {
  const [tension, setTension] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const save = async (value: number) => {
    if (busy) return;
    setBusy(true); setError('');
    try { await onSave(value); } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  };
  return <section className="panel exercise-panel">
    <span className="eyebrow">{moment === 'FINAL' ? 'Antes de ver tus resultados' : 'Una pausa para observar'}</span>
    <h2>¿Cuánta tensión percibes ahora?</h2>
    <p>Elige un número del 0 al 10. Esta respuesta describe cómo te sientes.</p>
    <div className="rating" role="group" aria-label="Tensión percibida de 0 a 10">
      {Array.from({ length: 11 }, (_, value) => <button type="button" key={value} aria-pressed={tension === value}
        className={tension === value ? 'selected' : ''} onClick={() => setTension(value)}>{value}</button>)}
    </div>
    <div className="rating-labels"><span>Sin tensión</span><span>Máxima tensión</span></div>
    {error && <p className="error-message" role="alert">{error}</p>}
    <div className="actions">
      <button className="button primary" disabled={busy || tension === null} onClick={() => tension !== null && void save(tension)}>Guardar y continuar</button>
    </div>
  </section>;
}
