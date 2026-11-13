# Protocolo, NeuroCode y límites de investigación

## Propósito y límites científicos

NeuroSync Care es una plataforma experimental universitaria de Biomedicina e Ingeniería de Software. Permite explorar indicadores EEG, percepción subjetiva y desempeño en tareas controladas. No es un dispositivo médico: no diagnostica trastornos, identifica emociones individuales ni convierte bandas en porcentajes clínicos de estrés.

El EEG de superficie refleja actividad agregada, no neuronas individuales ni conexiones sinápticas. La cabeza y el cerebro 3D son ilustraciones propias y las posiciones de electrodos son aproximadas; no representan anatomía individual ni reconstrucción de fuentes intracerebrales.

| Dato | Qué permite interpretar |
| --- | --- |
| Potencia por bandas | Valores `pow` recibidos por sensor, con su unidad. No es una onda EEG cruda, una FFT local completa ni un área cortical medida. |
| Calidad/contacto | Información de disponibilidad y contacto; no certifica ausencia de artefactos ni mide estrés. |
| Respuestas de actividad | Corrección, omisiones, intentos y tiempos; no inteligencia, competencia personal o productividad. |
| Autoevaluaciones | Tensión, dificultad, esfuerzo y comodidad expresados por la persona. Se guardan separados del EEG y no se inventan respuestas. |

El simulador se etiqueta `DATOS SIMULADOS` y usa `u.a. (simulado)`; sus patrones son ficticios. El dispositivo virtual de Launcher tampoco valida colocación física. Las sesiones con fuentes mezcladas incluyen la advertencia `mixed_sources`; la interfaz bloquea cambios de fuente durante una sesión.

Los huecos por pérdida de señal se contabilizan como ausentes y no se interpolan. Los colores de potencia pueden usar una escala automática entre cero y el máximo actual del montaje; el valor original siempre se conserva y la escala puede fijarse. [Controles de visualización](USER_GUIDE.md).

Los estadísticos EEG describen **medias de ventanas agregadas por sensor**, no la variabilidad ni los extremos de muestras originales. Las ventanas parciales conservan su conteo pero tienen el mismo peso en la estadística descriptiva actual. El informe no calcula significación estadística ni demuestra causalidad.

## Protocolo disponible

| Etapa | Registro | Estándar / demostración |
| --- | --- | --- |
| Preparación | Fuente, autorización de guardado y tensión inicial opcional | Sin límite impuesto |
| BASELINE | Potencia/calidad disponibles en reposo | 120 / 8 s |
| MATH o CODING | Desempeño y EEG registrados por separado | MATH: 120 / 8 s; CODING: 120 / 20 s |
| Autoevaluación posterior | Tensión; dificultad, esfuerzo y comodidad opcionales | Sin límite impuesto |
| REGULATION | Guía elegida y datos disponibles | 180 / 10 s |
| Evaluación final | Percepción subjetiva | Sin límite impuesto |
| Resultados | Descripción y exportación | — |

Las definiciones se publican en `GET /api/protocol`. El backend proporciona los instantes de fase y verifica los plazos de respuesta. El cliente cierra la referencia y coordina transiciones mientras el recorrido permanece montado; abandonar completamente el navegador no detiene la adquisición ni activa un planificador de cierre de fases. [Detalles de implementación](ARCHITECTURE.md).

En matemáticas se admiten hasta 20 respuestas por fase, incluidas omisiones. La exactitud es correctas / total enviado; la latencia media excluye omisiones. Los rangos de operandos son definiciones explícitas de dificultad, no mediciones fisiológicas.

Las autoevaluaciones usan 0–10. La tensión inicial es opcional; la posterior y final se piden al continuar. Las demás dimensiones son opcionales y un campo vacío se conserva como ausente.

La calma ofrece respiración suave 4–6, 4–4 y atención abierta al entorno, sin retenciones forzadas ni hiperventilación. Se puede pausar o detener la guía. La pausa afecta a la guía, no al registro EEG; los ritmos y mensajes son contenido definido de la actividad.

## NeuroCode implementado

Pregunta exploratoria: ¿cómo varían los indicadores EEG y el esfuerzo/tensión percibidos durante tareas de programación controladas, y qué asociaciones tienen con corrección, intentos y tiempo?

El piloto permite elegir comprensión de un recorrido o detección de un error de límite. Las dos tareas están versionadas y presentan fragmentos con opciones. El servidor comprueba la respuesta contra criterios del catálogo; no ejecuta código del participante ni afirma pruebas de software superadas.

Cada fase se vincula a una tarea conocida. Se registran opción, dificultad, número de intento, corrección e instante, con hasta tres intentos y un plazo del servidor. `elapsed_ms` cuenta desde el inicio de fase, no desde cada clic ni como latencia neuronal. Terminar la fase no implica resolverla: el informe incluye tareas sin respuesta entre las no resueltas.

`POST_CODING` recoge las autoevaluaciones posteriores y el CSV de código exporta los intentos. Estas respuestas no modifican la señal real. [Esquemas y endpoints](ARCHITECTURE.md).

## Antes de realizar un estudio

1. Definir tarea, dificultad, versión, duración, instrucciones y criterio de corrección antes de registrar datos.
2. Comprobar permisos de cuenta y calidad, anotar artefactos y acordar criterios de exclusión de tramos ausentes o contaminados.
3. Validar ejercicios, comodidad, accesibilidad y consentimiento con el equipo académico y participantes. La demostración rápida solo comprueba software.
4. Controlar práctica y fatiga, contrabalancear tareas cuando corresponda y definir muestra y métodos apropiados.
5. Comparar primero fases dentro de la misma persona, distinguiendo esa variación de las diferencias entre personas; reportar incertidumbre y posibles factores de confusión. Una correlación exploratoria no demuestra causalidad.

## Privacidad y retención

Guardar en historial empieza desmarcado y requiere autorización expresa. Las sesiones temporales también se escriben en SQLite: quedan fuera del historial y se descartan al salir de Resultados o al reiniciar el backend. Un cierre abrupto de pestaña o pérdida de red puede dejarlas en disco hasta ese reinicio. Los CSV descargados son copias independientes y no desaparecen al borrar una sesión.

Las bases, exportaciones privadas y credenciales están excluidas de Git. La aplicación está diseñada para uso local, sin autenticación multiusuario; la política de investigación debe definir acceso, conservación y eliminación de los datos obtenidos.

No hay captura de teclas, inspección de aplicaciones, acceso a repositorios privados, integración con un IDE, clasificaciones públicas ni vigilancia académica/laboral. Las líneas de código no son una medida principal de desempeño. Rapidez, corrección y esfuerzo son variables distintas.

## Futuro, todavía no implementado

Validar y ampliar el catálogo con niveles comparables; registrar marcas de estímulo y reproducción sincronizada; exportar un dataset con calidad y versión de protocolo; estudiar asociaciones con métodos adecuados. Un editor o ejecutor de código requeriría objetivos, consentimiento, aislamiento y límites de recursos específicos. No existe actualmente un clasificador de estrés ni un índice de productividad.
