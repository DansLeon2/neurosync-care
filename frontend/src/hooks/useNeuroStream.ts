import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import type {
  BandKey,
  RealtimeFrame,
  SensorLayout,
  SessionOut,
  SourceStatus,
} from '../types/neuro';
import { computeBandAverage } from '../utils/format';

export interface HistoryPoint {
  seq: number;
  timestamp: string;
  bands: Record<BandKey, number | null>;
  channels: Record<string, number | null>;
  overall_quality: number | null;
}

export interface LogEntry {
  id: string;
  time: string;
  tag: 'WS' | 'SUB' | 'IMP' | 'SYNC' | 'SES' | 'ERR';
  text: string;
}

const DEFAULT_STATUS: SourceStatus = {
  source: 'DISCONNECTED',
  simulated: false,
  connection: 'DISCONNECTED',
  integration_state: 'NOT_APPLICABLE',
  message: 'Conectando con el servidor NeuroSync Care…',
  device: null,
  scenario: null,
  last_sample_at: null,
  streams: [],
};

function nowStamp(): string {
  const d = new Date();
  return d.toLocaleTimeString('es-EC', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0');
}

export function useNeuroStream() {
  const [status, setStatus] = useState<SourceStatus>(DEFAULT_STATUS);
  const [frame, setFrame] = useState<RealtimeFrame | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [activeSession, setActiveSession] = useState<SessionOut | null>(null);
  const [layout, setLayout] = useState<SensorLayout | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const pushLog = useCallback((tag: LogEntry['tag'], text: string) => {
    setLogs((prev) => [
      ...prev.slice(-24),
      { id: `${Date.now()}-${Math.random()}`, time: nowStamp(), tag, text },
    ]);
  }, []);

  const refreshState = useCallback(async () => {
    try {
      const [st, sess, lay] = await Promise.all([
        api.getSourceStatus(),
        api.getActiveSession(),
        api.getLayout(),
      ]);
      setStatus(st);
      setActiveSession(sess);
      setLayout(lay);
    } catch (err) {
      pushLog('ERR', `No se pudo consultar el estado del backend: ${(err as Error).message}`);
    }
  }, [pushLog]);

  useEffect(() => {
    refreshState();
  }, [refreshState]);

  useEffect(() => {
    let closedByCleanup = false;
    let retryTimer: number | undefined;

    function connect() {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = import.meta.env.VITE_WS_URL || `${proto}//${window.location.host}/ws/stream`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        pushLog('WS', 'Canal de telemetría WebSocket conectado (/ws/stream).');
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'hello') {
            if (msg.status) setStatus(msg.status);
            setFrame(msg.status?.connection === 'STREAMING' ? msg.frame ?? null : null);
            setActiveSession(msg.session ?? null);
            pushLog(
              'SUB',
              `Estado inicial recibido — Fuente: ${msg.status?.source ?? 'DISCONNECTED'}.`
            );
          } else if (msg.type === 'frame') {
            const f = msg as RealtimeFrame;
            setFrame(f);
            const pt: HistoryPoint = {
              seq: f.seq,
              timestamp: f.timestamp,
              bands: {
                theta: computeBandAverage(f, 'theta'),
                alpha: computeBandAverage(f, 'alpha'),
                low_beta: computeBandAverage(f, 'low_beta'),
                high_beta: computeBandAverage(f, 'high_beta'),
                gamma: computeBandAverage(f, 'gamma'),
              },
              channels: {
                AF3: f.pow?.AF3?.alpha ?? null,
                F3: f.pow?.F3?.low_beta ?? null,
                O1: f.pow?.O1?.alpha ?? null,
                P7: f.pow?.P7?.theta ?? null,
              },
              overall_quality: f.overall_quality,
            };
            setHistory((prev) => [...prev.slice(-239), pt]);
            if (f.seq % 64 === 0) {
              pushLog(
                'SYNC',
                `Lote #${f.seq} procesado (${f.simulated ? 'SIMULATED 8 Hz' : f.source}). Calidad global: ${
                  f.overall_quality ?? '--'
                }%.`
              );
            }
          } else if (msg.type === 'status') {
            setStatus(msg.status);
            if (msg.status.connection !== 'STREAMING') { setFrame(null); setHistory([]); }
            pushLog(
              msg.status.connection === 'ERROR' || msg.status.connection === 'SIGNAL_LOST'
                ? 'ERR'
                : 'IMP',
              `Fuente [${msg.status.source}] → ${msg.status.connection}: ${msg.status.message}`
            );
          } else if (msg.type === 'session') {
            const s = msg.session as SessionOut;
            setActiveSession(s.status === 'ACTIVE' ? s : null);
            pushLog('SES', `Evento de sesión #${s.id}: ${msg.event}`);
          }
        } catch {
          // ignore malformed packet
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setStatus(previous => ({ ...previous, connection: 'DISCONNECTED', message: 'Se perdió la conexión con el servidor.' }));
        setFrame(null); setHistory([]);
        if (!closedByCleanup) {
          pushLog('ERR', 'WebSocket desconectado. Reintentando conexión en 2 s…');
          retryTimer = window.setTimeout(connect, 2000);
        }
      };
    }

    connect();
    return () => {
      closedByCleanup = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      wsRef.current?.close();
    };
  }, [pushLog]);

  const clearHistory = useCallback(() => {
    setHistory([]);
    setFrame(null);
  }, []);

  return {
    status,
    setStatus,
    frame,
    history,
    clearHistory,
    activeSession,
    setActiveSession,
    layout,
    setLayout,
    wsConnected,
    logs,
    pushLog,
    refreshState,
  };
}

