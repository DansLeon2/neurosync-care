import React, { useEffect, useState } from 'react';
import type { DataSource, SourceStatus } from '../../types/neuro';
import { useTelemetry } from '../telemetry/useTelemetry';
import { MODEL_GUIDES, MODEL_LABELS, PREPARATION_STEPS, modelInstructions, type HeadsetModel } from './preparationContent';

interface Props {
  source: DataSource; status: SourceStatus; onReady?: (ready: boolean) => void;
  onConnect: () => Promise<void>; disabled?: boolean;
}
export function DevicePreparation({ source, status, onReady, onConnect, disabled }: Props) {
  const { frame } = useTelemetry();
  const [model, setModel] = useState<HeadsetModel>('');
  const [step, setStep] = useState(0);
  const [confirmed, setConfirmed] = useState<boolean[]>([false,false,false,false,false,false]);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');
  const matching = status.source === source && status.connection === 'STREAMING';
  const actual = matching && frame?.source === source ? frame : null;
  const contacts = Object.entries(actual?.contact ?? {});
  const poor = contacts.filter(([, value]) => value === null || value < 3).map(([id]) => id);
  const hasPower = actual !== null && Object.values(actual.pow).some(values => Object.values(values).some(value => typeof value === 'number' && Number.isFinite(value)));
  const qualityKnown = contacts.length > 0;
  const ready = Boolean(model && confirmed.slice(0,3).every(Boolean) && confirmed[4] && confirmed[5] && matching && hasPower);
  useEffect(() => { onReady?.(ready); }, [ready, onReady]);
  useEffect(() => { setStep(0); setConfirmed([false,false,false,false,false,false]); }, [source]);
  const instructions = modelInstructions(model);
  const nextAllowed = step === 0 ? Boolean(model && confirmed[0]) : step < 3 ? confirmed[step] : step === 3 ? matching && hasPower : confirmed[step];
  return <section className="device-preparation" aria-label="Preparación guiada de EMOTIV">
    <div className="preparation-top"><span className="eyebrow">Preparar el dispositivo · {step + 1} / 6</span><button type="button" className="text-button" onClick={() => setStep(0)}>Revisar desde el inicio</button></div>
    <div className="preparation-progress" aria-hidden="true">{PREPARATION_STEPS.map((label,index) => <span key={label} className={index <= step ? 'active' : ''} />)}</div>
    <div className="preparation-body"><svg className="preparation-figure" data-step={step} viewBox="0 0 180 180" role="img" aria-label="Ilustración orientativa de preparación, no instrucciones anatómicas">
      <path d="M58 154 Q48 121 44 90 Q40 28 90 24 Q140 28 136 90 Q132 121 122 154" fill="var(--tint-soft)" stroke="var(--border-strong)" strokeWidth="2" />
      <path className="headset-guide" d="M42 95 Q20 45 90 35 Q160 45 138 95" fill="none" stroke="var(--accent)" strokeWidth="6" />
      {[55,78,102,125].map((x,index) => <circle key={x} cx={x} cy={index % 2 ? 57 : 79} r="7" fill="var(--accent)" className="preparation-sensor" />)}
      <text x="90" y="166" textAnchor="middle" fill="var(--text-faint)" fontSize="10">Ilustración propia</text>
    </svg><div className="preparation-copy"><h3>{PREPARATION_STEPS[step]}</h3>
      {step === 0 && <label className="field-label">Modelo de EMOTIV<select aria-label="Modelo de EMOTIV" value={model} onChange={event => { setModel(event.target.value as HeadsetModel); setConfirmed([false,false,false,false,false,false]); }}>
        {(Object.keys(MODEL_LABELS) as HeadsetModel[]).map(key => <option key={key} value={key}>{MODEL_LABELS[key]}</option>)}</select></label>}
      {step < 3 && <p>{instructions[step]}</p>}
      {step === 3 && <><p>Enciende el casco, conéctalo mediante un método compatible y abre EMOTIV Launcher en este mismo equipo. Aprueba la aplicación cuando lo solicite.</p>
        <button type="button" className="button subtle compact" disabled={connecting || disabled} onClick={async () => { setConnecting(true); setError(''); try { await onConnect(); } catch (err) { setError((err as Error).message); } finally { setConnecting(false); } }}>{connecting ? 'Conectando…' : 'Conectar fuente elegida'}</button>
        <p className="muted">Comprobación por software: {matching && hasPower ? 'recibiendo potencia del dispositivo seleccionado' : status.source === source ? status.message : 'fuente real/virtual todavía sin conectar'}.</p>
      </>}
      {step === 4 && <><p>Revisa la calidad por electrodo. Se muestra información recibida, sin sustituir valores ausentes.</p>
        <div className="quality-sensors">{contacts.length ? contacts.map(([id,value]) => <span key={id} data-good={value !== null && value >= 3}>{id}: {value ?? '—'} / 4</span>) : <span>Calidad de contacto no disponible.</span>}</div>
        <p className="muted">{poor.length ? `${poor.join(', ')}: contacto insuficiente o desconocido. Revisa su colocación según el fabricante.` : qualityKnown ? 'Contacto disponible para los sensores mostrados; esto no certifica una señal libre de artefactos.' : 'No se ha confirmado la calidad de contacto por software.'}</p>
      </>}
      {step === 5 && <p>Confirma que estás cómodo y que puedes detenerte cuando lo necesites. El estado de conexión procede del software; tu comodidad solo puedes confirmarla tú.</p>}
      {(step < 3 || step >= 4) && <label className="check-field"><input type="checkbox" checked={confirmed[step]} disabled={step === 0 && !model} onChange={event => setConfirmed(values => values.map((value,index) => index === step ? event.target.checked : value))} />{step === 5 ? 'Estoy cómodo y listo para comenzar' : step === 4 ? 'He revisado la calidad y comprendo las limitaciones indicadas' : 'He realizado esta revisión manualmente'}</label>}
      {model && <a className="text-button" href={MODEL_GUIDES[model]} target="_blank" rel="noreferrer">Consultar guía oficial de {MODEL_LABELS[model]} ↗</a>}
    </div></div>
    {error && <p role="alert" className="error-message">{error}</p>}
    <div className="actions"><button type="button" className="button subtle compact" disabled={step === 0} onClick={() => setStep(value => value - 1)}>Anterior</button>
      {step < 5 && <button type="button" className="button primary compact" disabled={!nextAllowed} onClick={() => setStep(value => value + 1)}>Siguiente paso</button>}
      {step === 5 && <span className="muted">{ready ? 'Preparación confirmada. Puedes comenzar la sesión.' : 'Completa las revisiones y comprueba que llegue señal.'}</span>}
    </div>
    {source === 'VIRTUAL_DEVICE' && <p className="muted">Dispositivo virtual: estos pasos sirven para aprender; no hay una colocación física comprobada.</p>}
  </section>;
}
