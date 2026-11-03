import React from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import type { SessionOut, SourceStatus } from '../types/neuro';
import { formatSourceLabel } from '../utils/format';

interface Props {
  status: SourceStatus;
  activeSession: SessionOut | null;
  wsConnected: boolean;
  onOpenStartSession: () => void;
  onFinishSession: () => Promise<void>;
}
export const TopHeader: React.FC<Props> = ({ status, activeSession, wsConnected, onOpenStartSession, onFinishSession }) =>
  <header className="app-header no-print">
    <div className="header-status">
      {wsConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
      <span>{wsConnected ? formatSourceLabel(status.source) : 'Sin conexión al servidor'}</span>
      <span className="status-dot" data-online={wsConnected && status.connection === 'STREAMING'} />
    </div>
    {activeSession
      ? <button type="button" className="button subtle" onClick={() => void onFinishSession()}>Detener sesión</button>
      : <button type="button" className="button primary compact" disabled={!wsConnected} onClick={onOpenStartSession}>Nueva sesión</button>}
  </header>;
