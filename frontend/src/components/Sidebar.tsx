import React, { useState } from 'react';
import { Activity, BarChart3, Brain, Calculator, Cpu, Wind } from 'lucide-react';
import type { NavTab, SessionOut, SourceStatus } from '../types/neuro';

interface Props {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  status: SourceStatus;
  activeSession: SessionOut | null;
}
const primary = [
  { id: 'dashboard', label: 'Mi sesión', icon: Activity },
  { id: 'neuroreport', label: 'Resultados', icon: BarChart3 },
  { id: 'hardware', label: 'Dispositivo', icon: Cpu },
] as const;
const advanced = [
  { id: 'neuromap', label: 'Explorar sensores', icon: Brain },
  { id: 'neurotest', label: 'Practicar operaciones', icon: Calculator },
  { id: 'neurocalma', label: 'Practicar calma', icon: Wind },
] as const;

export const Sidebar: React.FC<Props> = ({ activeTab, onSelectTab, activeSession }) => {
  const [expanded, setExpanded] = useState(false);
  const item = (entry: typeof primary[number] | typeof advanced[number]) => (
    <button key={entry.id} type="button" aria-current={activeTab === entry.id ? 'page' : undefined}
      className={`nav-item ${activeTab === entry.id ? 'selected' : ''}`}
      onClick={() => onSelectTab(entry.id)}>
      <entry.icon size={18} /><span>{entry.label}</span>
    </button>
  );
  return <aside className="app-sidebar no-print">
    <a className="brand" href="#main" onClick={() => onSelectTab('dashboard')}>
      <span className="brand-mark"><Activity size={23} /></span>
      <span>NeuroSync <strong>Care</strong><small>Explora · practica · observa</small></span>
    </a>
    <nav aria-label="Navegación principal">{primary.map(item)}</nav>
    <div className="advanced-nav">
      <button className="text-button" type="button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
        Herramientas {expanded ? '−' : '+'}
      </button>
      {(expanded || advanced.some(entry => entry.id === activeTab)) && <nav aria-label="Herramientas">{advanced.map(item)}</nav>}
    </div>
    <div className="sidebar-note">{activeSession ? `Sesión #${activeSession.id} en curso` : 'Tu próximo paso empieza aquí.'}<p>Proyecto experimental de biofeedback EEG.</p></div>
  </aside>;
};
