import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { DataSource, ProtocolOut } from '../types/neuro';
import { formatDuration } from '../utils/format';
interface Props {
  open: boolean; currentSource: DataSource; protocol: ProtocolOut; onClose: () => void;
  onStart: (opts: { consent_storage: boolean; test_mode: boolean; selectedSource: DataSource; initialTension: number | null }) => Promise<void>;
}
export const SessionStartModal: React.FC<Props> = ({ open, currentSource, protocol, onClose, onStart }) => {
  const [consent, setConsent] = useState(false);
  const [quick, setQuick] = useState(false);
  const [source, setSource] = useState<DataSource>('SIMULATED');
  const [tension, setTension] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const dialog = React.useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (open) {
      setSource(currentSource === 'DISCONNECTED' ? 'SIMULATED' : currentSource);
      setConsent(false); setQuick(false); setTension(null); setError('');
      if (!dialog.current?.open) dialog.current?.showModal();
    } else dialog.current?.close();
  }, [open, currentSource]);
  const total = protocol.phases.reduce((sum, value) => sum + (quick ? value.test_duration_s : value.default_duration_s), 0);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError('');
    try { await onStart({ consent_storage: consent, test_mode: quick, selectedSource: source, initialTension: tension }); onClose(); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  return <dialog ref={dialog} className="session-dialog" aria-labelledby="session-title" onCancel={event => { if (busy) event.preventDefault(); else onClose(); }}>
    <form onSubmit={submit}>
      <div className="section-top"><div><span className="eyebrow">Preparar</span><h2 id="session-title">Tu sesión, a tu ritmo.</h2></div><button type="button" className="icon-button" aria-label="Cerrar preparación" disabled={busy} onClick={onClose}><X size={20} /></button></div>
      <p>Referencia inicial → operaciones → calma → resultados. Tiempo de actividad: {formatDuration(total)}, más tus respuestas.</p>
      <label className="field-label">Fuente de datos<select value={source} disabled={busy} onChange={event => setSource(event.target.value as DataSource)}>
        <option value="SIMULATED">Simulador · sin casco · datos sintéticos</option><option value="VIRTUAL_DEVICE">Dispositivo virtual EMOTIV</option><option value="REAL_EMOTIV">Casco EMOTIV</option>
      </select></label>
      <fieldset disabled={busy}><legend>Tensión inicial (opcional)</legend><p className="muted">¿Cómo te sientes ahora? 0 = sin tensión · 10 = máxima tensión.</p>
        <div className="rating">{Array.from({ length: 11 }, (_, value) => <button type="button" key={value} aria-pressed={tension === value} className={tension === value ? 'selected' : ''} onClick={() => setTension(tension === value ? null : value)}>{value}</button>)}</div>
      </fieldset>
      <label className="check-field"><input type="checkbox" checked={consent} disabled={busy} onChange={event => setConsent(event.target.checked)} /><span>Guardar esta sesión en el historial local<small>Sin marcar: resultados temporales, fuera del historial. Se descartan al cerrar los resultados o reiniciar el servidor.</small></span></label>
      <details><summary>Opciones de demostración</summary><label className="check-field"><input type="checkbox" checked={quick} disabled={busy} onChange={event => setQuick(event.target.checked)} /><span>Usar duraciones cortas de demostración</span></label></details>
      <p className="muted">Plataforma experimental. No realiza diagnósticos. Puedes detenerte cuando lo necesites.</p>
      {error && <p className="error-message" role="alert">{error}</p>}
      <div className="actions"><button className="button primary" disabled={busy}>{busy ? 'Preparando…' : 'Comenzar sesión'}</button><button type="button" className="button subtle" disabled={busy} onClick={onClose}>Cancelar</button></div>
    </form>
  </dialog>;
};
