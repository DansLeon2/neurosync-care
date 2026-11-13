import React, { useState } from 'react';
import type { BandKey, SensorLayout, SourceStatus } from '../../types/neuro';
import type { LogEntry } from '../../hooks/useNeuroStream';
import { useTelemetry } from './useTelemetry';
import { LiveBandChart } from './LiveBandChart';
import { BAND_META, formatSourceLabel } from '../../utils/format';
import { SensorMap2D } from '../neuromap/SensorMap2D';
import { sensorReadings } from '../neuromap/sensorModel';

export function LiveTelemetryPanel({ status, layout, logs, onExplore }: { status: SourceStatus; layout: SensorLayout | null; logs: LogEntry[]; onExplore: () => void }) {
  const { frame, history } = useTelemetry();
  const [band, setBand] = useState<BandKey>('alpha');
  const [sensor, setSensor] = useState('ALL');
  const [seconds, setSeconds] = useState(30);
  const [tab, setTab] = useState<'time' | 'sensors' | 'events'>('time');
  const sensors = layout?.sensors ?? [];
  const selected = sensor === 'ALL' ? sensors[0]?.id ?? '' : sensor;
  const ceiling = Math.max(1, ...sensors.map(value => frame?.pow?.[value.id]?.[band] ?? 0));
  return <section className="panel live-telemetry" aria-label="Telemetría de la experiencia">
    <div className="section-top"><div><span className="eyebrow">Señal en vivo</span><h2>Observa lo que cambia.</h2></div><span className="pill">{formatSourceLabel(status.source)}</span></div>
    <div className="signal-summary"><span><i className="status-dot" data-online={status.connection === 'STREAMING'} /> {status.connection === 'STREAMING' ? 'Recibiendo datos' : 'Sin señal disponible'}</span><span>Calidad general: <strong>{frame?.overall_quality == null ? '—' : frame.overall_quality.toFixed(0) + '%'}</strong></span></div>
    {status.connection !== 'STREAMING' && <p className="muted" role="status">{status.message} Los huecos permanecen visibles; no se rellenan.</p>}
    <div className="explorer-filters"><label className="field-label">Banda<select aria-label="Banda de telemetría" value={band} onChange={event => setBand(event.target.value as BandKey)}>{(Object.keys(BAND_META) as BandKey[]).map(key => <option key={key} value={key}>{BAND_META[key].label}</option>)}</select></label>
      <label className="field-label">Sensor<select aria-label="Sensor de telemetría" value={sensors.some(value => value.id === sensor) ? sensor : 'ALL'} onChange={event => setSensor(event.target.value)}><option value="ALL">Media de sensores</option>{sensors.map(value => <option key={value.id}>{value.id}</option>)}</select></label>
      <label className="field-label">Ventana<select aria-label="Ventana temporal" value={seconds} onChange={event => setSeconds(Number(event.target.value))}>{[5,15,30,60].map(value => <option key={value} value={value}>{value} segundos</option>)}</select></label></div>
    <div className="segmented" role="group" aria-label="Detalle de telemetría">{([['time','Evolución'],['sensors','Sensores'],['events','Eventos']] as const).map(([key,label]) => <button key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>{label}</button>)}</div>
    {tab === 'time' && <LiveBandChart points={history} band={band} sensor={sensors.some(value => value.id === sensor) ? sensor : 'ALL'} seconds={seconds} unit={frame?.pow_unit ?? history.find(point => point.pow_unit)?.pow_unit ?? null} />}
    {tab === 'sensors' && <><SensorMap2D readings={sensorReadings(layout, frame, band, 'power', ceiling)} selected={selected} onSelect={setSensor} /><p className="muted">Color: potencia entre 0 y {ceiling.toFixed(2)} {frame?.pow_unit ?? ''}. Escala automática del instante actual.</p><button className="text-button" onClick={onExplore}>Abrir explorador 2D / 3D</button></>}
    {tab === 'events' && <ul className="log-list">{logs.length ? logs.slice(-10).map(log => <li key={log.id}>{log.time} · {log.text}</li>) : <li>Sin eventos todavía.</li>}</ul>}
    <details className="technical-details"><summary>Origen y unidades</summary><p>Potencia por banda del flujo pow, no EEG crudo ni una FFT completa. {frame?.pow_unit ?? 'Sin unidad disponible'}. {status.simulated ? 'Datos sintéticos del simulador.' : 'El estado de conexión no demuestra por sí solo ausencia de artefactos.'}</p><p>El búfer visual conserva hasta 1024 fotogramas y todas las bandas/sensores recibidos. Las actualizaciones visuales agrupadas no modifican el registro del backend.</p></details>
  </section>;
}
