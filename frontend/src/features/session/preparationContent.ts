export type HeadsetModel = '' | 'EPOCX' | 'EPOC_PLUS' | 'EPOC' | 'INSIGHT' | 'OTHER';
export const MODEL_LABELS: Record<HeadsetModel, string> = { '': 'Selecciona el modelo', EPOCX: 'EPOC X', EPOC_PLUS: 'EPOC+', EPOC: 'EPOC original', INSIGHT: 'Insight', OTHER: 'Otro modelo' };
export const MODEL_GUIDES: Record<HeadsetModel, string> = {
  '': 'https://www.emotiv.com/quick-start-guide-epoc-x',
  EPOCX: 'https://www.emotiv.com/quick-start-guide-epoc-x',
  EPOC_PLUS: 'https://www.emotiv.com/quick-start-guide-epoc-plus',
  EPOC: 'https://emotiv.gitbook.io/epoc-user-manual',
  INSIGHT: 'https://www.emotiv.com/quick-start-guide-insight',
  OTHER: 'https://emotiv.gitbook.io/emotiv-home',
};
export const PREPARATION_STEPS = ['Preparación', 'Electrodos', 'Colocación', 'Conexión', 'Calidad', 'Comodidad'];
export function modelInstructions(model: HeadsetModel): string[] {
  if (model === 'EPOCX' || model === 'EPOC_PLUS') return [
    'Comprueba la carga, los fieltros y el receptor compatible. Prepara el equipo siguiendo su guía oficial.',
    'Hidrata los fieltros con la solución indicada por EMOTIV y retira el exceso antes de montarlos. Manipula los sensores con higiene; no añadas mezclas caseras.',
    model === 'EPOCX' ? 'Ajusta EPOC X según su guía de orientación y colocación. Revisa el contacto con el cuero cabelludo sin forzar sus brazos.' : 'Coloca EPOC+ siguiendo la orientación y las referencias de su propia guía. No uses el ajuste de diadema de EPOC X como instrucción para este modelo.',
  ];
  if (model === 'INSIGHT') return [
    'Revisa la carga y el conjunto de sensores de polímero semiseco de Insight.',
    'Insight no usa los fieltros de EPOC X. Utiliza el líquido y el procedimiento de preparación específicos indicados por el fabricante para tu versión.',
    'Orienta las referencias hacia la piel detrás de la oreja izquierda y el sensor Pz hacia la zona superior/posterior. Ajusta siguiendo la guía de Insight.',
  ];
  return ['Identifica la versión y los accesorios con la persona responsable del equipo.', 'Consulta el material de electrodos y su preparación en el manual de este modelo. No se aplica automáticamente el procedimiento de EPOC X.', 'Sigue las posiciones y la orientación del manual correspondiente. Si no puedes confirmar el modelo, consulta al responsable del equipo antes de colocarlo.'];
}
