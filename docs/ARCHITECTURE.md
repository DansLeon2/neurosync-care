# Arquitectura y flujo

## Responsabilidades

```text
Simulador / EMOTIV Cortex
          |
AcquisitionService -> Pipeline -> StreamHub -> /ws/stream -> useNeuroStream
                         |
                  MeasurementRecorder
                         |
                       SQLite
                         |
 FastAPI REST -> sesiones / operaciones / autoevaluaciones / informes
                         |
          React: Mi sesión / Resultados / Dispositivo
```

La adquisición y la telemetría continúan independientemente de la pantalla visible. El backend mantiene la sesión y las fases; React reconstruye su progreso consultando la sesión y sus autoevaluaciones.

## Una única definición de protocolo

`backend/app/services/protocol.py` publica las fases, sus duraciones y la política matemática mediante `GET /api/protocol`. `SessionService` resuelve la duración omitida desde esa misma definición. `useProtocol` carga el contrato para las actividades y la preparación.

| Actividad | Estándar | Demostración |
| --- | ---: | ---: |
| Referencia | 120 s | 8 s |
| Operaciones | 120 s | 8 s |
| Calma | 180 s | 10 s |

Los siete momentos internos siguen existiendo para mantener compatibilidad con la API. La interfaz los agrupa en cuatro pasos: Preparar, Actividad, Calma y Resultados. Las autoevaluaciones son parte del recorrido y no pantallas adicionales.

## Estados de sesión y fase

- Solo una sesión `ACTIVE` por instancia local.
- Solo una fase activa; iniciar otra sin cerrar la anterior devuelve 409.
- El cliente cierra la referencia al cumplirse su tiempo y solicita la siguiente acción al participante.
- La actividad matemática termina en el cliente por tiempo, cantidad o decisión del participante.
- El servidor verifica el plazo matemático en cada emisión y respuesta, incluso si la pestaña está oculta.
- No hay un programador de cierre de fases en segundo plano: cerrar el navegador puede dejar una fase activa. Reiniciar el backend cierra sesiones huérfanas como interrumpidas.
- La pausa de la guía de calma detiene la animación y su contador local, mientras el EEG de la fase continúa. Al recargar, el tiempo se recupera desde el inicio de la fase; la pausa local no persiste.
- La finalización guiada produce `COMPLETED`; detener desde la cabecera produce `ABORTED`.

La API conserva fases manuales para experimentos locales; no impone el orden completo del asistente a los clientes externos. Sí impone que las respuestas cognitivas pertenezcan a una fase matemática activa.

## Integridad de operaciones

`MathService` genera sumas, restas no negativas y multiplicaciones enteras. Los operandos se acotan por dificultad. La política de sesión permite hasta 20 respuestas, incluidas omisiones, por fase y hasta 120 s. El cliente envía `null` únicamente al omitir explícitamente.

Cada pregunta contiene identificador completo, instante de emisión, caducidad, número de operación y límite. Se vincula al ID de la fase en que se emitió. Una emisión repetida en esa fase devuelve la misma pregunta pendiente. No se devuelven respuestas esperadas hasta corregir.

Las respuestas aceptan enteros estrictos entre -9999 y 9999, o `null`: no cadenas, booleanos ni decimales. La caducidad se comprueba tanto al emitir como al responder. Cambiar de fase o finalizar la sesión impide registrar una pregunta anterior.

Un bloqueo en memoria serializa la corrección para evitar doble registro por solicitudes simultáneas en un mismo proceso. Hay un máximo de 256 preguntas pendientes, con caducidad de 120 s. La práctica independiente no tiene sesión ni contador durable en el servidor; su ronda de 20 operaciones / 120 s se limita en el navegador. No es un mecanismo de cuotas multiusuario.

## Presentación de datos

- `useNeuroStream` conserva un búfer acotado de 240 puntos y lo limpia al desconectarse o perder señal.
- La telemetría está plegada por defecto. La curva alfa representa promedios reales de las bandas recibidas; las interrupciones separan los tramos.
- El mapa toma los sensores y coordenadas del montaje publicado por el backend. No asigna una emoción o un área cortical medida a un electrodo.
- Los valores sin datos se muestran como “—”. No se sustituyen con constantes ni senos artificiales.
- Resultados usa las mismas métricas que los CSV: aciertos / operaciones enviadas, incluidas omisiones; tiempo medio entre respuestas no omitidas.
- Las unidades proceden del flujo normalizado y se distinguen las fuentes simuladas.

## Persistencia y límites

SQLite almacena sesiones, fases, ventanas agregadas, respuestas, autoevaluaciones y eventos. El registrador promedia por ventana de un segundo y conserva conteos de muestras válidas y ausentes.

Las estadísticas de banda actuales describen los promedios de esas ventanas por sensor; no reconstruyen la desviación, mínimos ni máximos de la señal original a 8 Hz. Las ventanas parciales tienen el mismo peso en las estadísticas actuales. Véanse las limitaciones metodológicas.

Las sesiones temporales usan SQLite y se ocultan del historial. Se descartan al salir de Resultados mediante la API y se purgan al reiniciar. No constituyen almacenamiento exclusivamente en memoria.

Para despliegue multiusuario harían falta autenticación, aislamiento por participante, almacenamiento compartido de preguntas y coordinación transaccional entre procesos. La aplicación actual se ejecuta con un único worker local.
