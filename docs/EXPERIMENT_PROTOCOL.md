# Protocolo experimental configurable

La plataforma permite observar variaciones de indicadores EEG, percepción subjetiva y respuestas durante una actividad. No presupone que el estrés cause un cambio de desempeño ni que una banda mida estrés.

| Etapa | Registro | Duración estándar / demostración |
| --- | --- | --- |
| Preparación | Fuente, autorización y tensión inicial opcional | Sin límite impuesto |
| BASELINE | Potencia y calidad disponibles en reposo | 120 / 8 s |
| MATH o CODING | Respuestas y tiempo, por separado del EEG | 120 / 8 s en MATH; 120 / 20 s en CODING |
| Autoevaluación posterior | Tensión; dificultad, esfuerzo y comodidad opcionales | Sin límite impuesto |
| REGULATION | Guía elegida y datos disponibles | 180 / 10 s |
| Evaluación final | Percepción subjetiva | Sin límite impuesto |
| Resultados | Descripción de los datos y exportación | — |

Las duraciones y definiciones se publican en GET /api/protocol. El servidor da los instantes de fase y verifica los límites de respuestas. La referencia y las transiciones guiadas se cierran desde el cliente mientras el recorrido está montado. Cerrar completamente el navegador no detiene la adquisición; el backend no tiene un planificador de finalización automática de fases.

## Variables y criterios previos

- Definir antes de registrar la tarea, dificultad, versión, duración, instrucciones y criterio de corrección.
- En matemáticas: correctas, incorrectas, omitidas y tiempos; aciertos = correctas / todas las respuestas enviadas, incluidas omisiones.
- En código: tarea del catálogo versionado, opción elegida, hasta tres intentos, corrección y milisegundos desde el inicio de fase. Una fase terminada no implica una tarea resuelta.
- Autoevaluaciones 0–10 sin valores inventados: tensión obligatoria al continuar los momentos posteriores; las otras dimensiones son opcionales.
- Indicadores fisiológicos: bandas autorizadas, unidades, calidad y fuente. Documentar tramos ausentes o contaminados y criterios de exclusión.

La demostración rápida sirve para comprobar el software; no es un protocolo validado de investigación. Para un estudio formal deben definirse duración y muestra, controlar práctica y fatiga, contrabalancear tareas cuando corresponda, y acordar consentimiento y procedimiento con el equipo académico.

## Interpretación

Comparar primero fases dentro de la misma persona. Los niveles basales pueden variar entre participantes. Distinguir variación entre personas de variación dentro de una sesión. Una coincidencia temporal o correlación exploratoria no demuestra causalidad.

El informe actual proporciona estadísticas descriptivas. No calcula significación, causalidad ni un índice clínico. [Diseño de investigación NeuroCode](NEUROCODE_PROPOSAL.md) · [Limitaciones](SCIENTIFIC_LIMITATIONS.md).
