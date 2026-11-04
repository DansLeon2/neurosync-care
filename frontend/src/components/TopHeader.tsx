import React from 'react';
import { Moon, Sun, Wifi, WifiOff } from 'lucide-react';
import type { SessionOut, SourceStatus } from '../types/neuro';
import type { Theme } from '../hooks/useTheme';
import { formatSourceLabel } from '../utils/format';

interface Props {
  status: SourceStatus;
  activeSession: SessionOut | null;
  wsConnected: boolean;
  theme: Theme;
  onToggleTheme: () => void;
  onOpenStartSession: () => void;
  onFinishSession: () => Promise<void>;
}
export const TopHeader: React.FC<Props> = ({ status, activeSession, wsConnected, theme, onToggleTheme, onOpenStartSession, onFinishSession }) =>
  <header className="app-header no-print">
    <div className="header-status">
      {wsConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
      <span>{wsConnected ? formatSourceLabel(status.source) : 'Sin conexión al servidor'}</span>
      <span className="status-dot" data-online={wsConnected && status.connection === 'STREAMING'} />
    </div>
    <div className="header-actions">
      <button type="button" className="theme-toggle" onClick={onToggleTheme}
        aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
        title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}>
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      {activeSession
        ? <button type="button" className="button subtle" onClick={() => void onFinishSession()}>Detener sesión</button>
        : <button type="button" className="button primary compact" disabled={!wsConnected} onClick={onOpenStartSession}>Nueva sesión</button>}
    </div>
  </header>;
