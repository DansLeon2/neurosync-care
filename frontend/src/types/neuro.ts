export type DataSource = 'SIMULATED' | 'VIRTUAL_DEVICE' | 'REAL_EMOTIV' | 'DISCONNECTED';

export type ConnectionState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'STREAMING'
  | 'SIGNAL_LOST'
  | 'ERROR';

export type IntegrationState =
  | 'NOT_APPLICABLE'
  | 'CONNECTING'
  | 'CORTEX_NOT_INSTALLED'
  | 'CORTEX_UNAVAILABLE'
  | 'CREDENTIALS_MISSING'
  | 'CREDENTIALS_INVALID'
  | 'AUTHORIZATION_PENDING'
  | 'DEVICE_NOT_FOUND'
  | 'DEVICE_DISCONNECTED'
  | 'STREAM_NOT_AUTHORIZED'
  | 'CONNECTED_STREAMING'
  | 'COMMUNICATION_ERROR';

export type SimulatorScenario =
  | 'NORMAL'
  | 'VARIABLE_POWER'
  | 'POOR_QUALITY'
  | 'TEMPORARY_DISCONNECT'
  | 'NO_OPTIONAL_METRICS'
  | 'ACTIVITY_DEMO';

export type BandKey = 'theta' | 'alpha' | 'low_beta' | 'high_beta' | 'gamma';

export type PhaseKind = 'BASELINE' | 'MATH' | 'REGULATION';
export type PhaseStatus = 'ACTIVE' | 'COMPLETED' | 'ABORTED';
export type SessionStatus = 'ACTIVE' | 'COMPLETED' | 'ABORTED';
export type ReportMoment = 'INITIAL' | 'POST_MATH' | 'FINAL' | 'OTHER';
export type MathDifficulty = 'EASY' | 'MEDIUM' | 'HARD';
export type MathOperation = 'ADD' | 'SUBTRACT' | 'MULTIPLY';
export type AnswerResult = 'CORRECT' | 'INCORRECT' | 'SKIPPED';

export type NavTab =
  | 'dashboard'
  | 'neuromap'
  | 'neurotest'
  | 'neurocalma'
  | 'neuroreport'
  | 'hardware';

export interface DeviceInfo {
  id: string | null;
  model: string | null;
  is_virtual: boolean | null;
  connected_by: string | null;
  firmware: string | null;
  sensors: string[];
  battery_percent: number | null;
}

export interface StreamCapability {
  stream: string;
  label: string;
  state: 'available' | 'unavailable' | 'not_authorized' | 'unknown' | 'disabled';
  rate_hz: number | null;
  note: string | null;
}

export interface SourceStatus {
  source: DataSource;
  simulated: boolean;
  connection: ConnectionState;
  integration_state: IntegrationState;
  message: string;
  device: DeviceInfo | null;
  scenario: SimulatorScenario | null;
  last_sample_at: string | null;
  streams: StreamCapability[];
}

export interface SimulatorConfig {
  scenario: SimulatorScenario;
  seed: number;
  poor_sensors: string[];
}

export interface SensorPosition {
  id: string;
  x: number;
  y: number;
}

export interface SensorLayout {
  model: string;
  label: string;
  sensors: SensorPosition[];
  note: string;
}

export interface RealtimeFrame {
  type: 'frame';
  seq: number;
  timestamp: string;
  source: DataSource;
  simulated: boolean;
  device_model: string | null;
  pow: Record<string, Partial<Record<BandKey, number | null>>>;
  pow_unit: string | null;
  quality: Record<string, number | null>;
  contact: Record<string, number | null>;
  overall_quality: number | null;
  sample_rate_quality: number | null;
  battery_percent: number | null;
  signal: number | null;
  met: Record<string, number | null> | null;
}

export interface PhaseOut {
  id: number;
  session_id: number;
  kind: PhaseKind;
  detail: string | null;
  planned_duration_s: number | null;
  started_at: string;
  ended_at: string | null;
  status: PhaseStatus;
}

export interface SessionOut {
  id: number;
  started_at: string;
  ended_at: string | null;
  data_source: DataSource;
  status: SessionStatus;
  consent_storage: boolean;
  device_model: string | null;
  test_mode: boolean;
  duration_s: number | null;
  phases: PhaseOut[];
}

export interface SessionListItem {
  id: number;
  started_at: string;
  ended_at: string | null;
  duration_s: number | null;
  data_source: DataSource;
  status: SessionStatus;
  test_mode: boolean;
  activities: PhaseKind[];
  tension_initial: number | null;
  tension_final: number | null;
  math_total: number;
  math_correct: number;
}

export interface SelfReportOut {
  id: number;
  session_id: number;
  phase_id: number | null;
  moment: ReportMoment;
  tension: number;
  difficulty: number | null;
  comfort: number | null;
  note: string | null;
  timestamp: string;
}

export interface CognitiveAnswerOut {
  id: number;
  session_id: number;
  phase_id: number | null;
  question_id: string;
  question_text: string;
  operation: MathOperation;
  difficulty: MathDifficulty;
  given_answer: number | null;
  expected_answer: number;
  result: AnswerResult;
  response_time_ms: number;
  timestamp: string;
}

export interface DeviceEventOut {
  id: number;
  session_id: number | null;
  event: string;
  detail: string | null;
  source: string | null;
  timestamp: string;
}

export interface SessionDetail {
  session: SessionOut;
  self_reports: SelfReportOut[];
  answers: CognitiveAnswerOut[];
  events: DeviceEventOut[];
}

export interface MathQuestionOut {
  question_id: string;
  text: string;
  operation: MathOperation;
  difficulty: MathDifficulty;
  issued_at: string;
  expires_at: string;
  question_number: number;
  max_questions: number;
  recorded: boolean;
}

export interface MathAnswerOut {
  question_id: string;
  result: AnswerResult;
  given_answer: number | null;
  expected_answer: number;
  response_time_ms: number;
  recorded: boolean;
}

export interface BandStats {
  band: BandKey;
  mean: number | null;
  std: number | null;
  minimum: number | null;
  maximum: number | null;
  n_valid_samples: number;
  n_valid_bins: number;
  n_missing: number;
}

export interface PhaseStats {
  phase_id: number;
  kind: PhaseKind;
  detail: string | null;
  status: PhaseStatus;
  started_at: string;
  ended_at: string | null;
  planned_duration_s: number | null;
  duration_s: number | null;
  bands: BandStats[];
  quality: { mean_overall_quality: number | null; n_points: number };
  sources: string[];
  sufficient: boolean;
  insufficient_reason: string | null;
}

export interface MathStats {
  n_questions: number;
  n_answered: number;
  n_correct: number;
  n_incorrect: number;
  n_skipped: number;
  accuracy_pct: number | null;
  mean_response_time_ms: number | null;
  median_response_time_ms: number | null;
  duration_s: number | null;
}

export interface SessionSummary {
  session_id: number;
  status: string;
  data_source: string;
  duration_s: number | null;
  sources_present: string[];
  mixed_sources: boolean;
  simulated_data: boolean;
  total_measurement_rows: number;
  phases: PhaseStats[];
  math: MathStats | null;
  self_reports: {
    moment: ReportMoment;
    tension: number;
    difficulty: number | null;
    comfort: number | null;
    timestamp: string;
  }[];
  tension_changes: {
    label: string;
    from_moment: ReportMoment;
    to_moment: ReportMoment;
    change: number;
  }[];
  events_count: number;
  note: string;
}

export interface BandDelta {
  band: BandKey;
  mean_a: number | null;
  mean_b: number | null;
  absolute_change: number | null;
  percent_change: number | null;
}

export interface PhaseComparison {
  session_id: number;
  phase_a: PhaseStats | null;
  phase_b: PhaseStats | null;
  available: boolean;
  reason: string | null;
  deltas: BandDelta[];
  note: string;
}

export interface TimeseriesPoint {
  t: number;
  timestamp: string;
  values: Record<string, number | null>;
  phase_id: number | null;
}

export interface TimeseriesOut {
  session_id: number;
  bin_seconds: number;
  bands: BandKey[];
  points: TimeseriesPoint[];
  quality_points: TimeseriesPoint[];
  unit: string | null;
  simulated_data: boolean;
}

export interface ProtocolPhaseDef {
  key: string;
  label: string;
  description: string;
  default_duration_s: number;
  test_duration_s: number;
  kind: PhaseKind | null;
}

export interface ProtocolOut {
  math: { max_questions: number; question_ttl_s: number; answer_min: number; answer_max: number };
  phases: ProtocolPhaseDef[];
  disclaimer: string;
}

