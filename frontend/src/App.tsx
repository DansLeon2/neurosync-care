import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { SessionStartModal } from './components/SessionStartModal';
import { DashboardPage } from './pages/DashboardPage';
import { NeuroMapPage } from './pages/NeuroMapPage';
import { NeuroTestPage } from './pages/NeuroTestPage';
import { NeuroCalmaPage } from './pages/NeuroCalmaPage';
import { NeuroReportPage } from './pages/NeuroReportPage';
import { HardwarePage } from './pages/HardwarePage';
import { useNeuroStream } from './hooks/useNeuroStream';
import { useProtocol } from './hooks/useProtocol';
import { useTheme } from './hooks/useTheme';
import { api } from './services/api';
import type { DataSource, NavTab } from './types/neuro';

export const App: React.FC = () => {
  const { status, frame, history, activeSession, layout, wsConnected, logs, pushLog, refreshState, clearHistory } = useNeuroStream();
  const { protocol, error: protocolError, retry } = useProtocol();
  const { theme, toggle: toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [showStartModal, setShowStartModal] = useState(false);
  const [selectedReportSessionId, setSelectedReportSessionId] = useState<number | null>(null);
  const [temporaryResult, setTemporaryResult] = useState<number | null>(null);
  const [error, setError] = useState('');
  const finishing = React.useRef(false);

  const navigate = (tab: NavTab) => {
    if (tab !== 'neuroreport' && temporaryResult !== null) {
      const id = temporaryResult;
      setTemporaryResult(null); setSelectedReportSessionId(null);
      api.discardSession(id).catch(err => setError(`No se pudo descartar el resultado temporal: ${(err as Error).message}`));
    }
    setActiveTab(tab);
  };
  const startSession = async (opts: { consent_storage: boolean; test_mode: boolean; selectedSource: DataSource; initialTension: number | null }) => {
    setError('');
    const source = status.source !== opts.selectedSource
      ? await api.selectSource(opts.selectedSource) : await api.getSourceStatus();
    if (source.connection !== 'STREAMING') throw new Error(source.message || 'La fuente de datos aún no está lista.');
    const created = await api.startSession(opts.consent_storage, opts.test_mode);
    navigate('dashboard'); clearHistory();
    try {
      if (opts.initialTension !== null) await api.addSelfReport(created.id, { moment: 'INITIAL', tension: opts.initialTension });
      await api.startPhase(created.id, 'BASELINE');
      pushLog('SES', `Sesión #${created.id} preparada.`);
    } finally { await refreshState(); }
  };
  const finishSession = async (completed = false) => {
    if (!activeSession || finishing.current) return;
    finishing.current = true; setError('');
    try {
      const finished = await api.finishSession(activeSession.id, completed ? 'COMPLETED' : 'ABORTED');
      setSelectedReportSessionId(finished.id);
      if (!finished.consent_storage) setTemporaryResult(finished.id);
      await refreshState(); setActiveTab('neuroreport');
    } catch (err) { setError((err as Error).message); throw err; }
    finally { finishing.current = false; }
  };
  return <div className="app-shell">
    <a className="skip-link" href="#main">Ir al contenido</a>
    <Sidebar activeTab={activeTab} onSelectTab={navigate} status={status} activeSession={activeSession} />
    <TopHeader status={status} activeSession={activeSession} wsConnected={wsConnected} theme={theme} onToggleTheme={toggleTheme}
      onOpenStartSession={() => setShowStartModal(true)}
      onFinishSession={async () => { try { await finishSession(false); } catch { /* visible error */ } }} />
    <main id="main" className="app-main" tabIndex={-1}>
      {error && <div className="workspace"><p className="error-message" role="alert">{error}</p></div>}
      {!protocol ? <div className="workspace"><section className="panel"><h1>Conectando con NeuroSync Care</h1><p role="status">{protocolError || 'Cargando el protocolo de sesión…'}</p><button className="button primary" onClick={retry}>Reintentar conexión</button></section></div> : <>
        {activeTab === 'dashboard' && <DashboardPage status={status} frame={frame} history={history} logs={logs} activeSession={activeSession} protocol={protocol} onNavigate={navigate} onOpenStartSession={() => setShowStartModal(true)} onRefreshState={refreshState} onFinish={() => finishSession(true)} />}
        {activeTab === 'neuromap' && <NeuroMapPage status={status} frame={frame} layout={layout} />}
        {activeTab === 'neurotest' && <div className="workspace"><div className="page-title"><span className="eyebrow">Herramientas</span><h1>Practicar operaciones</h1><p>Una ronda independiente. Para registrar una actividad, vuelve a Mi sesión.</p></div>{activeSession ? <section className="panel"><p>Tu sesión está en curso. Continúa allí para mantener el registro.</p><button className="button primary" onClick={() => navigate('dashboard')}>Volver a mi sesión</button></section> : <NeuroTestPage activeSession={null} protocol={protocol} />}</div>}
        {activeTab === 'neurocalma' && <div className="workspace"><div className="page-title"><span className="eyebrow">Herramientas</span><h1>Practicar calma</h1><p>Una guía independiente. Para registrar una actividad, vuelve a Mi sesión.</p></div>{activeSession ? <section className="panel"><p>Tu sesión está en curso. Continúa allí para mantener el registro.</p><button className="button primary" onClick={() => navigate('dashboard')}>Volver a mi sesión</button></section> : <NeuroCalmaPage activeSession={null} protocol={protocol} />}</div>}
        {activeTab === 'neuroreport' && <NeuroReportPage selectedSessionId={selectedReportSessionId} onSelectSessionId={setSelectedReportSessionId} temporarySessionId={temporaryResult} onCloseTemporary={() => navigate('dashboard')} />}
        {activeTab === 'hardware' && <HardwarePage status={status} frame={frame} layout={layout} activeSession={activeSession} onRefreshState={refreshState} />}
      </>}
      <footer className="app-footer">NeuroSync Care · Plataforma experimental universitaria. No es un dispositivo médico ni realiza diagnósticos.</footer>
    </main>
    {protocol && <SessionStartModal open={showStartModal} currentSource={status.source} protocol={protocol} onClose={() => setShowStartModal(false)} onStart={startSession} />}
  </div>;
};
