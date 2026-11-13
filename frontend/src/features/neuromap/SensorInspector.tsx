import type { RealtimeFrame } from '../../types/neuro';
import type { SensorReading } from './sensorModel';
import { sensorRegion } from './sensorModel';
import { BAND_META } from '../../utils/format';
export function SensorInspector({ reading, frame }: { reading: SensorReading | undefined; frame: RealtimeFrame | null }) {
  if (!reading) return <div className="sensor-inspector"><p>Selecciona un electrodo para consultar sus datos.</p></div>;
  return <aside className="sensor-inspector" aria-label="Inspector de sensor">
    <span className="eyebrow">Sensor seleccionado</span><h3 data-testid="selected-sensor">{reading.id}</h3><p>{sensorRegion(reading.id)}</p>
    <dl className="inspector-quality"><div><dt>Contacto</dt><dd>{reading.contact ?? '—'} / 4</dd></div><div><dt>Calidad EEG</dt><dd>{reading.quality ?? '—'} / 4</dd></div></dl>
    <div className="sensor-bands">{(Object.keys(BAND_META) as (keyof typeof BAND_META)[]).map(band => <div key={band}><span>{BAND_META[band].label}</span><strong data-band={band}>{frame?.pow?.[reading.id]?.[band]?.toFixed(2) ?? '—'}</strong></div>)}</div>
    <p className="muted">{frame?.pow_unit ?? 'Sin unidad disponible'}<br />{frame ? new Date(frame.timestamp).toLocaleTimeString('es') : 'Sin muestra disponible'}</p>
  </aside>;
}
