import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { config } from '../services/config';
import { telemetry } from '../features/telemetry/streamStore';
import type { SessionOut, SourceStatus, SensorLayout, RealtimeFrame } from '../types/neuro';

export interface LogEntry {
  id: string; time: string;
  tag: 'WS' | 'SUB' | 'IMP' | 'SYNC' | 'SES' | 'ERR';
  text: string;
}
const DEFAULT_STATUS: SourceStatus = {
  source: 'DISCONNECTED', simulated: false, connection: 'DISCONNECTED',
  integration_state: 'NOT_APPLICABLE', message: 'Conectando con NeuroSync Care…',
  device: null, scenario: null, last_sample_at: null, streams: [],
};

/** One connection for the whole app; high-rate frames never update App state. */
export function useNeuroStream() {
  const [status, setStatus] = useState<SourceStatus>(DEFAULT_STATUS);
  const [activeSession, setActiveSession] = useState<SessionOut | null>(null);
  const [layout, setLayout] = useState<SensorLayout | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const generation = useRef(0);
  const pushLog = useCallback((tag: LogEntry['tag'], text: string) => {
    setLogs(previous => [...previous.slice(-24), {
      id: crypto.randomUUID(), time: new Date().toLocaleTimeString('es', { hour12: false }), tag, text,
    }]);
  }, []);
  const refreshState = useCallback(async () => {
    const request = ++generation.current;
    try {
      const [nextStatus, session, nextLayout] = await Promise.all([api.getSourceStatus(), api.getActiveSession(), api.getLayout()]);
      if (request !== generation.current) return;
      setStatus(nextStatus); setActiveSession(session); setLayout(nextLayout);
    } catch (error) {
      pushLog('ERR', (error as Error).message);
      throw error;
    }
  }, [pushLog]);
  useEffect(() => { void refreshState().catch(() => {}); }, [refreshState]);

  useEffect(() => {
    let disposed = false;
    let current: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let lastSource = '';
    let lastLayoutKey = '';
    const active = (socket: WebSocket) => !disposed && current === socket;
    function connect() {
      if (disposed) return;
      const socket = new WebSocket(config.websocketUrl);
      current = socket;
      socket.onopen = () => { if (active(socket)) { setWsConnected(true); pushLog('WS', 'Telemetría conectada.'); } };
      socket.onmessage = event => {
        if (!active(socket)) return;
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'frame') {
            telemetry.ingest(message as RealtimeFrame);
          } else if (message.type === 'hello' || message.type === 'status') {
            const nextStatus = message.status as SourceStatus;
            if (!nextStatus) return;
            if (lastSource && lastSource !== nextStatus.source) telemetry.clear();
            const layoutKey = `${nextStatus.source}:${nextStatus.device?.model ?? ''}:${nextStatus.device?.sensors.join(',') ?? ''}`;
            if (lastLayoutKey !== layoutKey) {
              lastLayoutKey = layoutKey;
              void api.getLayout().then(value => { if (active(socket)) setLayout(value); }).catch(() => {});
            }
            lastSource = nextStatus.source;
            setStatus(nextStatus);
            if (nextStatus.connection !== 'STREAMING') telemetry.gap();
            if (message.type === 'hello') {
              ++generation.current;
              setActiveSession(message.session ?? null);
              if (nextStatus.connection === 'STREAMING' && message.frame) telemetry.ingest(message.frame);
            } else {
              pushLog(nextStatus.connection === 'ERROR' || nextStatus.connection === 'SIGNAL_LOST' ? 'ERR' : 'IMP', nextStatus.message);
            }
          } else if (message.type === 'session') {
            ++generation.current;
            const session = message.session as SessionOut;
            setActiveSession(session.status === 'ACTIVE' ? session : null);
            pushLog('SES', `Sesión #${session.id}: ${message.event}`);
          }
        } catch { pushLog('ERR', 'Se descartó un mensaje de telemetría inválido.'); }
      };
      socket.onclose = () => {
        if (!active(socket)) return;
        setWsConnected(false);
        setStatus(previous => ({ ...previous, connection: 'DISCONNECTED', message: 'Se perdió la conexión con el servidor.' }));
        telemetry.gap();
        retry = setTimeout(connect, config.reconnectMs);
      };
      socket.onerror = () => { /* onclose schedules the single reconnect */ };
    }
    connect();
    return () => {
      disposed = true;
      if (retry !== undefined) clearTimeout(retry);
      current?.close();
      telemetry.flush();
    };
  }, [pushLog]);
  return { status, activeSession, layout, wsConnected, logs, pushLog, refreshState, clearHistory: telemetry.clear };
}
