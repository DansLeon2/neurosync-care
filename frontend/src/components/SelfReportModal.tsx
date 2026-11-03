import React, { useState } from 'react';
import { CheckCircle2, Sliders, X } from 'lucide-react';
import type { ReportMoment } from '../types/neuro';

interface SelfReportModalProps {
  open: boolean;
  defaultMoment?: ReportMoment;
  onClose: () => void;
  onSubmit: (payload: {
    moment: ReportMoment;
    tension: number;
    difficulty: number | null;
    comfort: number | null;
    note: string | null;
  }) => Promise<void>;
}

const MOMENT_LABELS: Record<ReportMoment, string> = {
  INITIAL: 'Evaluación Inicial (Antes de iniciar actividades)',
  POST_MATH: 'Post-Actividad Cognitiva (Tras NeuroTest)',
  FINAL: 'Evaluación Final (Tras Autorregulación)',
  OTHER: 'Registro Subjetivo Adicional',
};

export const SelfReportModal: React.FC<SelfReportModalProps> = ({
  open,
  defaultMoment = 'INITIAL',
  onClose,
  onSubmit,
}) => {
  const [moment, setMoment] = useState<ReportMoment>(defaultMoment);
  const [tension, setTension] = useState<number>(5);
  const [difficulty, setDifficulty] = useState<number>(4);
  const [comfort, setComfort] = useState<number>(7);
  const [includeOptional, setIncludeOptional] = useState<boolean>(true);
  const [note, setNote] = useState<string>('');
  const [saving, setSaving] = useState(false);

  React.useEffect(() => {
    setMoment(defaultMoment);
  }, [defaultMoment, open]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSubmit({
        moment,
        tension,
        difficulty: includeOptional ? difficulty : null,
        comfort: includeOptional ? comfort : null,
        note: note.trim() ? note.trim() : null,
      });
      setNote('');
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-2xl bg-surface-container-low border border-outline-variant/40 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 bg-surface-container border-b border-outline-variant/25">
          <div className="flex items-center gap-2.5">
            <Sliders className="w-5 h-5 text-primary" />
            <h2 className="font-headline text-lg font-bold text-on-surface">
              Autoevaluación Subjetiva del Participante
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label className="font-mono text-xs uppercase tracking-wider text-secondary">
              Momento de la sesión
            </label>
            <select
              value={moment}
              onChange={(e) => setMoment(e.target.value as ReportMoment)}
              className="bg-surface-container-lowest text-on-surface rounded-xl px-3.5 py-2.5 border border-outline-variant/40 text-sm outline-none focus:border-primary"
            >
              {(Object.keys(MOMENT_LABELS) as ReportMoment[]).map((m) => (
                <option key={m} value={m}>
                  {MOMENT_LABELS[m]}
                </option>
              ))}
            </select>
          </div>

          {/* Primary Question */}
          <div className="p-5 rounded-xl bg-surface-container-lowest border border-outline-variant/25 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-on-surface">
                ¿Cuánta tensión percibes en este momento?
              </span>
              <span className="font-mono text-lg font-bold text-primary">{tension} / 10</span>
            </div>
            <input
              type="range"
              min={0}
              max={10}
              step={1}
              value={tension}
              onChange={(e) => setTension(Number(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
            <div className="flex justify-between font-mono text-[11px] text-outline">
              <span>0 · Ninguna tensión percibida</span>
              <span>5 · Moderada</span>
              <span>10 · Máxima tensión percibida</span>
            </div>
          </div>

          {/* Optional Sliders */}
          <div className="flex flex-col gap-3">
            <label className="inline-flex items-center gap-2 text-xs text-on-surface-variant cursor-pointer">
              <input
                type="checkbox"
                checked={includeOptional}
                onChange={(e) => setIncludeOptional(e.target.checked)}
                className="accent-primary rounded"
              />
              <span>Incluir percepción de comodidad y dificultad (opcional)</span>
            </label>

            {includeOptional && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-surface-container border border-outline-variant/20 flex flex-col gap-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-on-surface-variant">¿Qué tan difícil fue?</span>
                    <span className="font-mono font-bold text-secondary">{difficulty} / 10</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={10}
                    value={difficulty}
                    onChange={(e) => setDifficulty(Number(e.target.value))}
                    className="w-full accent-secondary cursor-pointer"
                  />
                </div>

                <div className="p-4 rounded-xl bg-surface-container border border-outline-variant/20 flex flex-col gap-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-on-surface-variant">¿Qué tan cómoda te resultó?</span>
                    <span className="font-mono font-bold text-tertiary">{comfort} / 10</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={10}
                    value={comfort}
                    onChange={(e) => setComfort(Number(e.target.value))}
                    className="w-full accent-tertiary cursor-pointer"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="font-mono text-xs uppercase tracking-wider text-on-surface-variant">
              ¿Cómo describirías tu experiencia? (Opcional)
            </label>
            <input
              type="text"
              maxLength={300}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Ej. Mayor tranquilidad al respirar, fatiga ligera en las multiplicaciones…"
              className="bg-surface-container text-on-surface rounded-xl px-3.5 py-2.5 text-sm border border-outline-variant/30 outline-none focus:border-primary"
            />
          </div>

          <p className="text-xs text-outline leading-relaxed">
            Nota metodológica: Estas respuestas son percepciones subjetivas del participante. Se
            almacenan por separado de las potencias EEG y no constituyen ningún diagnóstico.
          </p>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl bg-surface-container text-on-surface-variant hover:text-on-surface text-sm font-medium"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-on-primary hover:bg-primary-fixed font-semibold text-sm shadow-lg"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{saving ? 'Guardando…' : 'Registrar Autoevaluación'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

