import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';
import type { PhaseKind, ProtocolOut, SessionDetail, SessionOut } from '../../types/neuro';

export function useGuidedSession(session: SessionOut | null, protocol: ProtocolOut, refresh: () => Promise<void>) {
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [now, setNow] = useState(Date.now());
  const lock = useRef(false);
  const phase = session?.phases.find(value => value.status === 'ACTIVE');
  const signature = session?.phases.map(value => value.id + value.status).join(',');
  const loadDetail = useCallback(async () => {
    if (session) setDetail(await api.getSessionDetail(session.id)); else setDetail(null);
  }, [session?.id]);
  useEffect(() => {
    let alive = true;
    if (!session) { setDetail(null); return; }
    void api.getSessionDetail(session.id).then(value => { if (alive) setDetail(value); }).catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, [session?.id, signature]);
  useEffect(() => {
    if (phase?.kind !== 'BASELINE') return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(timer);
  }, [phase?.id]);
  const action = useCallback(async (work: () => Promise<void>) => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try { await work(); } catch (err) { setError((err as Error).message); }
    finally { lock.current = false; setBusy(false); }
  }, []);
  const start = async (kind: PhaseKind, phaseDetail?: string) => {
    if (!session) return;
    await api.startPhase(session.id, kind, undefined, phaseDetail); await refresh();
  };
  const end = useCallback(async () => {
    if (!session || !phase) return;
    await api.endPhase(session.id, phase.id); await refresh();
  }, [session?.id, phase?.id, refresh]);
  const baseline = protocol.phases.find(value => value.kind === 'BASELINE')!;
  const baselineRemaining = phase?.kind === 'BASELINE' ? Math.max(0, Math.ceil((Date.parse(phase.started_at) + (phase.planned_duration_s ?? baseline.default_duration_s) * 1000 - now) / 1000)) : null;
  useEffect(() => { if (baselineRemaining === 0 && !busy && !error) void action(end); }, [baselineRemaining, busy, error, action, end]);
  const completed = (kind: PhaseKind) => session?.phases.some(value => value.kind === kind && value.status === 'COMPLETED') ?? false;
  const hasReport = (moment: string) => detail?.self_reports.some(report => report.moment === moment) ?? false;
  return { detail, busy, error, action, phase, baselineRemaining, completed, hasReport, loadDetail, start, end };
}
