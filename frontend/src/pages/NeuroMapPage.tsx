import React, { useEffect, useState } from 'react';
import type { BandKey, RealtimeFrame, SensorLayout, SourceStatus } from '../types/neuro';
import { BAND_META, formatSourceLabel } from '../utils/format';
interface Props { status: SourceStatus; frame: RealtimeFrame | null; layout: SensorLayout | null; }
export const NeuroMapPage: React.FC<Props> = ({ status, frame, layout }) => {
  const [band, setBand] = useState<BandKey>('alpha');
  const [selected, setSelected] = useState('');
  useEffect(() => { if (!layout?.sensors.some(sensor => sensor.id === selected)) setSelected(layout?.sensors[0]?.id ?? ''); }, [layout, selected]);
  const value = (sensor: string) => frame?.pow?.[sensor]?.[band] ?? null;
  const available = layout?.sensors.map(sensor => value(sensor.id)).filter((v): v is number => v !== null && Number.isFinite(v)) ?? [];
  const max = Math.max(...available, 1);
  return <div className="workspace">
    <div className="page-title"><span className="eyebrow">Herramientas · {formatSourceLabel(status.source)}</span><h1>Explorar sensores</h1><p>Potencia recibida por electrodo y banda, en una vista superior aproximada.</p></div>
    <section className="panel">
      <div className="section-top"><h2>{layout?.label ?? 'Esperando dispositivo'}</h2><label>Banda <select value={band} onChange={event => setBand(event.target.value as BandKey)}>
        {(Object.keys(BAND_META) as BandKey[]).map(key => <option key={key} value={key}>{BAND_META[key].label}</option>)}</select></label></div>
      <div className="sensor-layout"><svg viewBox="0 0 400 400" role="img" aria-label="Posiciones aproximadas de los electrodos">
        <circle cx="200" cy="200" r="166" fill="none" stroke="currentColor" opacity=".25" /><path d="M180 34 L200 12 L220 34" fill="none" stroke="currentColor" opacity=".4" />
        <text x="200" y="63" textAnchor="middle" fill="currentColor" fontSize="10">FRENTE</text>
        {layout?.sensors.map(sensor => <g key={sensor.id} transform={`translate(${200 + sensor.x * 166},${200 - sensor.y * 166})`}>
          <circle r="23" fill={value(sensor.id) === null ? '#e5e7eb' : '#e4ddf5'} stroke={selected === sensor.id ? '#6d4bb5' : '#a8a2b7'} strokeWidth={selected === sensor.id ? 2 : 1} />
          <text textAnchor="middle" dy="4" fill="#352c49" fontSize="12">{sensor.id}</text>
        </g>)}
      </svg><div><label className="field-label">Sensor<select value={selected} onChange={event => setSelected(event.target.value)}>{layout?.sensors.map(sensor => <option key={sensor.id}>{sensor.id}</option>)}</select></label>
        <h3>{selected || 'Sin sensor'}</h3><p>Contacto: {frame?.contact?.[selected] ?? '—'} / 4</p><p>Calidad: {frame?.quality?.[selected] ?? '—'} / 4</p>
        <div className="sensor-bands">{(Object.keys(BAND_META) as BandKey[]).map(key => <div key={key}><span>{BAND_META[key].label}</span><strong>{frame?.pow?.[selected]?.[key]?.toFixed(2) ?? '—'}</strong></div>)}</div><small>{frame?.pow_unit ?? 'Unidad no disponible'}</small>
      </div></div>
      <div className="sensor-grid">{layout?.sensors.map(sensor => <button key={sensor.id} className={selected === sensor.id ? 'selected' : ''} onClick={() => setSelected(sensor.id)}>
        <strong>{sensor.id}</strong><span>{value(sensor.id)?.toFixed(2) ?? 'Sin dato'}</span><span className="sensor-bar" style={{ width: value(sensor.id) === null ? 0 : (value(sensor.id)! / max) * 100 + '%' }} /></button>)}</div>
      <p className="muted">{layout?.note} Los valores ausentes se muestran como “—”. Las barras comparan valores de la banda seleccionada en este instante.</p>
    </section>
  </div>;
};
