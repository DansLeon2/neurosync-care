# NeuroCode: piloto implementado y siguiente investigación

## Pregunta

¿Cómo varían los indicadores EEG disponibles y el esfuerzo/tensión percibidos durante tareas de programación controladas, y qué asociaciones exploratorias tienen con corrección, intentos y tiempo?

No se parte de una relación causal ni se construye un clasificador clínico de estrés. La unidad de comparación inicial es la variación dentro de la misma persona.

## Implementado

La preparación permite elegir MATH o CODING. El registro de actividades se define en backend/app/services/activity_registry.py. MATH conserva el identificador y el contrato previo.

El piloto CODING contiene dos tareas versionadas: comprender un recorrido y detectar un error de límite. Se presentan un fragmento y opciones de respuesta. La corrección se realiza en el servidor contra criterios definidos en el catálogo; no se ejecuta código del participante ni se afirman pruebas de software superadas.

Cada fase se vincula a una tarea conocida. Se registran opción, dificultad, número de intento, corrección e instante. Hay hasta tres intentos y un plazo del servidor. El tiempo elapsed_ms se mide desde el inicio de la fase, no desde cada clic ni como latencia neuronal.

El resultado distingue tareas resueltas y sin resolver, incluidas las que no recibieron respuesta. Las autoevaluaciones POST_CODING admiten tensión, dificultad, esfuerzo y comodidad. Ninguna respuesta modifica el EEG real ni produce una puntuación de productividad.

## Contratos aditivos

- SessionCreate.activity_kind: MATH por defecto; CODING opcional.
- PhaseKind.CODING y ReportMoment.POST_CODING, sin renombrar valores previos.
- GET /api/coding/tasks: catálogo sin respuestas esperadas.
- POST /api/coding/answers: session_id, task_id, choice; exige fase, tarea y plazo válidos.
- SessionDetail.coding_answers y SessionSummary.coding.
- CSV dataset=coding; esfuerzo añadido al final del CSV de autoevaluaciones.

La tabla coding_answers es nueva. sessions.activity_kind y self_reports.effort se incorporan mediante migraciones aditivas. Las sesiones anteriores quedan como MATH.

## Futuro, no implementado

1. Validar los ejercicios con participantes y ampliar el catálogo con niveles comparables.
2. Registrar marcas temporales específicas de estímulo y permitir reproducción sincronizada.
3. Añadir tareas externas controladas o edición de código únicamente con objetivos y consentimiento definidos. Un ejecutor requeriría aislamiento y límites de recursos, y queda fuera de este piloto.
4. Exportar un dataset de investigación con política de exclusión, calidad y versión del protocolo.
5. Examinar asociaciones exploratorias con métodos apropiados, reportando incertidumbre y posibles variables de confusión.

No hay integración con VS Code, captura de teclas, inspección de aplicaciones, recolección de repositorios privados, comparaciones públicas de participantes ni vigilancia académica/laboral. Las líneas de código no son una medida principal de desempeño. Rapidez, corrección y esfuerzo son variables distintas.
