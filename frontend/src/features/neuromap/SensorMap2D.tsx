import React from 'react';
import type { SensorReading } from './sensorModel';
interface Props { readings: SensorReading[]; selected: string; onSelect: (id: string) => void; showSensors?: boolean; }
export function SensorMap2D({ readings, selected, onSelect, showSensors = true }: Props) {
  return <svg className="head-map" viewBox="0 0 400 420" role="group" aria-label="Mapa de electrodos, vista superior aproximada">
    <ellipse cx="200" cy="210" rx="166" ry="178" fill="var(--tint-soft)" stroke="var(--border-strong)" />
    <path d="M180 35 L200 12 L220 35 M32 180 Q8 210 32 240 M368 180 Q392 210 368 240" fill="none" stroke="var(--text-faint)" />
    <text x="200" y="65" textAnchor="middle" className="chart-text">FRENTE</text>
    <text x="200" y="410" textAnchor="middle" className="chart-text">IZQUIERDA ← participante → DERECHA</text>
    {showSensors && readings.map(sensor => <g key={sensor.id} role="button" tabIndex={0} aria-label={`Seleccionar ${sensor.id}`} aria-pressed={selected === sensor.id}
      onClick={() => onSelect(sensor.id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(sensor.id); } }}
      transform={`translate(${200 + sensor.x * 166},${210 - sensor.y * 178})`}>
      <circle r="23" fill={sensor.color} stroke={selected === sensor.id ? 'var(--accent)' : 'var(--surface)'} strokeWidth={selected === sensor.id ? 4 : 2} />
      <text textAnchor="middle" dy="4" fill="#241832" fontSize="11" fontWeight="600">{sensor.id}</text>
      <title>{sensor.id} · potencia {sensor.value ?? 'sin dato'} · contacto {sensor.contact ?? 'sin dato'} / 4</title>
    </g>)}
  </svg>;
}
