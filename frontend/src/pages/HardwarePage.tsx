import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { DataSource, RealtimeFrame, SensorLayout, SessionOut, SimulatorConfig, SimulatorScenario, SourceStatus } from '../types/neuro';
import { formatSourceLabel } from '../utils/format';
interface Props { status: SourceStatus; frame: RealtimeFrame | null; layout: SensorLayout | null; activeSession: SessionOut | null; onRefreshState: () => Promise<void>; }
export const HardwarePage: React.FC<Props> = ({ status, frame, layout, activeSession, onRefreshState }) => {
  const [config, setConfig] = useState<SimulatorConfig | null>(null);
  const [scenarios, setScenarios] = useState<{ id: SimulatorScenario; description: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => {
    let alive = true;
    Promise.all([api.getSimulatorConfig(), api.getSimulatorScenarios()]).then(([value, list]) => { if (alive) { setConfig(value); setScenarios(list); } })
      .catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, []);
  const action = async (work: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try { await work(); await onRefreshState(); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  const sources: { id: DataSource; label: string; description: string }[] = [
    { id: 'SIMULATED', label: 'Simulador', description: 'Empieza sin casco, con datos sintéticos.' },
    { id: 'VIRTUAL_DEVICE', label: 'EMOTIV virtual', description: 'Requiere un dispositivo virtual configurado en EMOTIV Launcher.' },
    { id: 'REAL_EMOTIV', label: 'Casco EMOTIV', description: 'Conecta tu dispositivo mediante Cortex.' },
  ];
  return <div className="workspace"><div className="page-title"><span className="eyebrow">Configuración</span><h1>Tu fuente de datos</h1><p>Elige cómo recibir la señal antes de comenzar la sesión.</p></div>
    {error && <p className="error-message" role="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
    {activeSession && <p className="notice">La fuente está bloqueada durante la sesión para mantener sus datos consistentes. Termina la sesión para cambiarla.</p>}
    <div className="source-options">{sources.map(source => <section className={`panel source-card ${status.source === source.id ? 'selected' : ''}`} key={source.id}>
      <h2>{source.label}</h2><p>{source.description}</p><button className="button subtle" disabled={busy || Boolean(activeSession) || status.source === source.id && status.connection === 'STREAMING'}
        onClick={() => void action(async () => { const result = await api.selectSource(source.id); setNotice(result.message); })}>{status.source === source.id && status.connection === 'STREAMING' ? 'En uso' : 'Conectar'}</button>
    </section>)}</div>
    <section className="panel"><div className="section-top"><h2>Estado de conexión</h2><button className="text-button" disabled={busy} onClick={() => void action(async () => {})}>Actualizar</button></div>
      <dl className="connection-list"><div><dt>Fuente</dt><dd>{formatSourceLabel(status.source)}</dd></div><div><dt>Estado</dt><dd>{status.connection === 'STREAMING' ? 'Recibiendo datos' : status.connection === 'CONNECTING' ? 'Conectando' : 'Sin señal disponible'}</dd></div>
        <div><dt>Montaje</dt><dd>{layout?.label ?? '—'}</dd></div><div><dt>Batería</dt><dd>{frame?.battery_percent == null ? '—' : frame.battery_percent + '%'}</dd></div><div><dt>Sensores</dt><dd>{status.device?.sensors.length ?? '—'}</dd></div></dl>
      <p>{status.message}</p>
      <button className="text-button" disabled={busy || Boolean(activeSession) || status.source === 'DISCONNECTED'} onClick={() => void action(async () => { await api.selectSource('DISCONNECTED'); })}>Desconectar fuente</button>
    </section>
    <details className="panel technical-details"><summary>Opciones del simulador y diagnóstico</summary>
      {config ? <fieldset disabled={busy || Boolean(activeSession)}><label className="field-label">Escenario<select value={config.scenario} onChange={event => setConfig({ ...config, scenario: event.target.value as SimulatorScenario })}>{scenarios.map(scenario => <option key={scenario.id} value={scenario.id}>{scenario.description}</option>)}</select></label>
        <label className="field-label">Semilla reproducible<input type="number" value={config.seed} onChange={event => setConfig({ ...config, seed: Number(event.target.value) })} /></label>
        <label className="field-label">Sensores con contacto deficiente</label><div className="sensor-grid">{layout?.sensors.map(sensor => <label className="check-field" key={sensor.id}><input type="checkbox" checked={config.poor_sensors.includes(sensor.id)} onChange={event => setConfig({ ...config, poor_sensors: event.target.checked ? [...config.poor_sensors, sensor.id] : config.poor_sensors.filter(id => id !== sensor.id) })} />{sensor.id}</label>)}</div>
        <div className="actions"><button className="button primary" onClick={() => void action(async () => { setConfig(await api.updateSimulatorConfig(config)); setNotice('Configuración aplicada.'); })}>Aplicar configuración</button>
          <button className="button subtle" disabled={status.source !== 'SIMULATED'} onClick={() => void action(async () => { await api.simulateDisconnect(6); })}>Simular pérdida de señal</button>
          <button className="button subtle" disabled={status.source !== 'SIMULATED'} onClick={() => void action(async () => { await api.simulatorReconnect(); })}>Reconectar simulador</button></div>
      </fieldset> : <p>Configuración no disponible. Vuelve a abrir esta pantalla para reintentar.</p>}
      <div className="table-scroll"><table><thead><tr><th>Flujo</th><th>Disponibilidad</th><th>Frecuencia</th></tr></thead><tbody>{status.streams.map(stream => <tr key={stream.stream}><td>{stream.label}</td><td>{stream.state}</td><td>{stream.rate_hz == null ? '—' : stream.rate_hz + ' Hz'}</td></tr>)}</tbody></table></div>
      <p className="muted">EMOTIV requiere Launcher, credenciales de backend y los permisos de la cuenta. El estado disponible aquí no sustituye una prueba con el casco físico.</p>
    </details>
  </div>;
};
