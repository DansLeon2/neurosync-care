import { useSyncExternalStore } from 'react';
import { telemetry } from './streamStore';

/** Only the views that draw live data subscribe; App keeps session state separately. */
export function useTelemetry() {
  return useSyncExternalStore(telemetry.subscribe, telemetry.getSnapshot, telemetry.getSnapshot);
}
