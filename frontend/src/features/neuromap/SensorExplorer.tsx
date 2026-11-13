import React, { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import type { BandKey, RealtimeFrame, SensorLayout } from '../../types/neuro';
import { BAND_META } from '../../utils/format';
import { sensorReadings, finite, type SensorColorMode } from './sensorModel';
import { SensorMap2D } from './SensorMap2D';
import { SensorInspector } from './SensorInspector';
const BrainScene = lazy(() => import('./BrainScene'));

export function SensorExplorer({ layout, frame, band, onBandChange }: { layout: SensorLayout | null; frame: RealtimeFrame | null; band: BandKey; onBandChange: (band: BandKey) => void }) {
  const [view, setView] = useState<'2d' | '3d'>('2d');
  const [selected, setSelected] = useState('');
  const [mode, setMode] = useState<SensorColorMode>('power');
  const [fixed, setFixed] = useState<number | null>(null);
  const [showSensors, setShowSensors] = useState(true);
  const [fallback, setFallback] = useState('');
  useEffect(() => { if (!layout?.sensors.some(sensor => sensor.id === selected)) setSelected(layout?.sensors[0]?.id ?? ''); }, [layout, selected]);
  const automatic = Math.max(1, ...(layout?.sensors ?? []).map(sensor => finite(frame?.pow?.[sensor.id]?.[band]) ?? 0));
  const ceiling = mode === 'quality' ? 4 : fixed ?? automatic;
  const readings = useMemo(() => sensorReadings(layout, frame, band, mode, ceiling), [layout, frame, band, mode, ceiling]);
  const unavailable = React.useCallback((reason: string) => { setFallback(reason); setView('2d'); }, []);
  return <section className="panel sensor-explorer">
    <div className="section-top"><div><span className="eyebrow">{layout?.label ?? 'Sin montaje'}</span><h2>Un mismo dato, dos perspectivas.</h2></div>
      <div className="segmented" role="group" aria-label="Tipo de vista"><button aria-pressed={view === '2d'} onClick={() => setView('2d')}>Vista 2D</button><button aria-pressed={view === '3d'} onClick={() => { setFallback(''); setView('3d'); }}>Vista 3D</button></div>
    </div>
    <div className="explorer-filters">
      <label className="field-label">Banda<select aria-label="Banda del explorador" value={band} onChange={event => onBandChange(event.target.value as BandKey)}>{(Object.keys(BAND_META) as BandKey[]).map(key => <option key={key} value={key}>{BAND_META[key].label}</option>)}</select></label>
      <label className="field-label">Color según<select value={mode} onChange={event => setMode(event.target.value as SensorColorMode)}><option value="power">Potencia por banda</option><option value="quality">Calidad EEG / contacto</option></select></label>
      <label className="field-label">Sensor<select aria-label="Sensor del explorador" value={selected} onChange={event => setSelected(event.target.value)}>{readings.map(sensor => <option key={sensor.id}>{sensor.id}</option>)}</select></label>
      <label className="check-field"><input type="checkbox" checked={showSensors} onChange={event => setShowSensors(event.target.checked)} />Mostrar sensores</label>
    </div>
    {fallback && <p className="notice" role="status">{fallback}</p>}
    <div className="explorer-grid"><div className="model-surface">
      {view === '2d' ? <SensorMap2D readings={readings} selected={selected} onSelect={setSelected} showSensors={showSensors} />
        : <Suspense fallback={<p className="chart-empty" role="status">Preparando la vista 3D…</p>}><BrainScene readings={readings} selected={selected} showSensors={showSensors} onSelect={setSelected} onUnavailable={unavailable} /></Suspense>}
    </div><SensorInspector reading={readings.find(sensor => sensor.id === selected)} frame={frame} /></div>
    <div className="color-legend"><span>0</span><span className={mode === 'power' ? 'power-gradient' : 'quality-gradient'} /><span>{ceiling.toFixed(mode === 'quality' ? 0 : 2)} {mode === 'quality' ? '/ 4' : frame?.pow_unit ?? ''}</span><span>Gris: sin dato</span>
      {mode === 'power' && <button className="text-button" onClick={() => setFixed(fixed === null ? automatic : null)}>{fixed === null ? 'Fijar escala actual' : 'Usar escala automática'}</button>}
    </div>
    <details className="technical-details"><summary>Cómo interpretar esta representación</summary><p>El color muestra {mode === 'power' ? 'potencia recibida, normalizada linealmente entre 0 y el límite de la leyenda' : 'calidad EEG o contacto cuando la calidad no está disponible'}. {mode === 'power' && fixed === null ? 'La escala automática usa el máximo actual de los sensores; no permite interpretar cambios de color como cambios absolutos entre instantes.' : 'La escala es fija mientras permanezca seleccionada.'} El inspector siempre conserva el valor original.</p><p>{layout?.note} El cerebro interior es una ilustración procedimental propia. No es una reconstrucción individual ni una localización intracerebral. No se muestran conexiones neuronales inferidas.</p></details>
  </section>;
}
