import type {
  DataSource,
  MathAnswerOut,
  MathDifficulty,
  MathQuestionOut,
  PhaseComparison,
  PhaseKind,
  PhaseOut,
  ProtocolOut,
  ReportMoment,
  SelfReportOut,
  SensorLayout,
  SessionDetail,
  SessionListItem,
  SessionOut,
  SessionSummary,
  SimulatorConfig,
  SimulatorScenario,
  SourceStatus,
  TimeseriesOut,
} from '../types/neuro';

const API_BASE = import.meta.env.VITE_API_BASE || '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    let detail = `Error HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err && typeof err.detail === 'string') detail = err.detail;
      else if (Array.isArray(err?.detail)) detail = err.detail.map((item: { msg: string }) => item.msg).join('. ');
    } catch {
      // ignore json parse error
    }
    throw new Error(detail);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () =>
    request<{ status: string; version: string; database: string; websocket_clients: number }>(
      '/api/health'
    ),
  getProtocol: () => request<ProtocolOut>('/api/protocol'),
  getSourceStatus: () => request<SourceStatus>('/api/source/status'),
  selectSource: (source: DataSource, force = false) =>
    request<SourceStatus>('/api/source/select', {
      method: 'POST',
      body: JSON.stringify({ source, force }),
    }),
  getLayout: () => request<SensorLayout>('/api/source/layout'),
  getLayouts: () => request<SensorLayout[]>('/api/layouts'),
  getSimulatorConfig: () => request<SimulatorConfig>('/api/simulator/config'),
  getSimulatorScenarios: () =>
    request<{ id: SimulatorScenario; description: string }[]>('/api/simulator/scenarios'),
  updateSimulatorConfig: (payload: Partial<SimulatorConfig>) =>
    request<SimulatorConfig>('/api/simulator/config', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  startSimulator: (force = false) =>
    request<SourceStatus>(`/api/simulator/start?force=${force}`, { method: 'POST' }),
  stopSimulator: (force = false) =>
    request<SourceStatus>(`/api/simulator/stop?force=${force}`, { method: 'POST' }),
  simulateDisconnect: (duration_s: number | null = 5) =>
    request<SourceStatus>('/api/simulator/disconnect', {
      method: 'POST',
      body: JSON.stringify({ duration_s }),
    }),
  simulatorReconnect: () =>
    request<SourceStatus>('/api/simulator/reconnect', { method: 'POST' }),

  // Sesiones
  startSession: (consent_storage: boolean, test_mode: boolean) =>
    request<SessionOut>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ consent_storage, test_mode }),
    }),
  getActiveSession: () => request<SessionOut | null>('/api/sessions/active'),
  finishSession: (sessionId: number, status: 'COMPLETED' | 'ABORTED' = 'COMPLETED') =>
    request<SessionOut>(`/api/sessions/${sessionId}/finish`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),
  discardSession: (sessionId: number) =>
    request<{ discarded: boolean }>(`/api/sessions/${sessionId}/discard`, {
      method: 'POST',
    }),
  listSessions: () => request<SessionListItem[]>('/api/sessions'),
  getSessionDetail: (sessionId: number) =>
    request<SessionDetail>(`/api/sessions/${sessionId}`),
  getSessionSummary: (sessionId: number) =>
    request<SessionSummary>(`/api/sessions/${sessionId}/summary`),
  comparePhases: (sessionId: number, a: string, b: string) =>
    request<PhaseComparison>(
      `/api/sessions/${sessionId}/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`
    ),
  getSessionTimeseries: (sessionId: number) =>
    request<TimeseriesOut>(`/api/sessions/${sessionId}/timeseries`),
  deleteSession: (sessionId: number) =>
    request<void>(`/api/sessions/${sessionId}`, { method: 'DELETE' }),
  deleteAllSessions: () =>
    request<{ deleted: number }>('/api/sessions', { method: 'DELETE' }),

  // Fases
  startPhase: (
    sessionId: number,
    kind: PhaseKind,
    planned_duration_s?: number,
    detail?: string
  ) =>
    request<PhaseOut>(`/api/sessions/${sessionId}/phases`, {
      method: 'POST',
      body: JSON.stringify({ kind, planned_duration_s, detail }),
    }),
  endPhase: (
    sessionId: number,
    phaseId: number,
    status: 'COMPLETED' | 'ABORTED' = 'COMPLETED'
  ) =>
    request<PhaseOut>(`/api/sessions/${sessionId}/phases/${phaseId}/end`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),

  // Autoevaluaciones
  addSelfReport: (
    sessionId: number,
    payload: {
      moment: ReportMoment;
      tension: number;
      difficulty?: number | null;
      comfort?: number | null;
      note?: string | null;
      phase_id?: number | null;
    }
  ) =>
    request<SelfReportOut>(`/api/sessions/${sessionId}/self-reports`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Matemáticas
  issueMathQuestion: (difficulty: MathDifficulty, session_id?: number | null) =>
    request<MathQuestionOut>('/api/math/questions', {
      method: 'POST',
      body: JSON.stringify({ difficulty, session_id: session_id ?? null }),
    }),
  submitMathAnswer: (question_id: string, answer: number | null) =>
    request<MathAnswerOut>('/api/math/answers', {
      method: 'POST',
      body: JSON.stringify({ question_id, answer }),
    }),

  getExportUrl: (
    sessionId: number,
    dataset: 'measurements' | 'answers' | 'self_reports' | 'summary'
  ) => `${API_BASE}/api/sessions/${sessionId}/export.csv?dataset=${dataset}`,
};

