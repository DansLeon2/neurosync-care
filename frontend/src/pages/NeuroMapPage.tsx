import React, { useState } from 'react';
import type { BandKey, SensorLayout, SourceStatus } from '../types/neuro';
import { formatSourceLabel } from '../utils/format';
import { useTelemetry } from '../features/telemetry/useTelemetry';
import { SensorExplorer } from '../features/neuromap/SensorExplorer';

export const NeuroMapPage: React.FC<{ status: SourceStatus; layout: SensorLayout | null }> = ({ status, layout }) => {
  const { frame } = useTelemetry();
  const [band, setBand] = useState<BandKey>('alpha');
  return <div className="workspace explorer-workspace">
    <div className="page-title"><span className="eyebrow">Explorador · {formatSourceLabel(status.source)}</span><h1>Otra perspectiva de tu señal.</h1><p>Explora los sensores sobre una cabeza ilustrativa. Los datos corresponden al cuero cabelludo, sin localizar fuentes dentro del cerebro.</p></div>
    {status.simulated && <p className="notice">Datos sintéticos. El modelo 3D es ilustrativo y los valores provienen del simulador.</p>}
    <SensorExplorer layout={layout} frame={frame} band={band} onBandChange={setBand} />
  </div>;
};
