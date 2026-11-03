# Auditoría y mejoras

## Problemas confirmados y cambios

| Hallazgo | Cambio |
| --- | --- |
| Seis módulos competían por la atención y el participante debía decidir el orden | Tres destinos principales y un recorrido guiado de cuatro pasos en una sola pantalla |
| El cronómetro matemático llegaba a cero sin impedir nuevas respuestas | Bloqueo de entrada, cierre del ejercicio en el cliente y verificación del plazo en el servidor |
| No había máximo de operaciones por fase | 20 respuestas por fase, incluidas omisiones; límite comprobado contra respuestas almacenadas |
| Las respuestas podían registrarse sin fase matemática o en una fase posterior | Vinculación explícita con la fase original y rechazo fuera de contexto |
| La caducidad solo se depuraba al emitir otras preguntas | Verificación también al corregir, incluso sin una nueva emisión |
| Emisiones repetidas y respuestas concurrentes podían causar inconsistencias | Reutilización de pregunta pendiente y bloqueo por proceso durante emisión/corrección |
| Duraciones duplicadas y contradictorias entre protocolo y pantallas | Valores del protocolo consumidos por frontend y servidor |
| Se guardaba comodidad = 7 sin haberla preguntado | Eliminado; solo se guardan respuestas expresas |
| Consentimiento de historial y demostración venían preseleccionados | Ambos comienzan desmarcados |
| Ondas de seno/coseno parecían mediciones de canales reales | Curva de potencia recibida; huecos visibles y sin osciloscopio sintético |
| Mapa saturado de zonas corticales, FFT y conexiones artísticas | Electrodos, contacto y potencia por banda; sin localizar actividad cortical |
| La precisión en pantalla y en informes usaba denominadores distintos | Aciertos / total enviado, incluidas omisiones, y latencia solo de respuestas no omitidas |
| Cambiar fuente forzaba el cambio durante una sesión | Fuente bloqueada en la interfaz durante la sesión y llamadas sin force |
| Detener manualmente marcaba siempre completada | Detención marcada como interrumpida |
| La navegación fija ocupaba demasiado espacio y no se adaptaba a móvil | Navegación compacta, disposición móvil y herramientas secundarias plegadas |
| Los fallos de operaciones se ignoraban | Mensajes visibles y recuperación explícita, sin reintentos infinitos |
| Faltaba claridad sobre datos temporales | Descarte al salir de resultados y documentación de retención real en SQLite |

## Decisiones visuales

Fondo claro, violeta moderado, tarjetas con espacio, lenguaje directo y una acción principal por etapa. Teclado numérico, telemetría, comparación EEG y diagnóstico están disponibles a demanda.

La calma ofrece tres guías sin retenciones; la animación respeta la preferencia de movimiento reducido. Los formularios usan controles con etiquetas y el diálogo de preparación ofrece foco modal y cierre por Escape.

## Qué conserva configuración fija y por qué

- Los rangos de operandos son una definición explícita de dificultad en MathService.
- Los ritmos de respiración y mensajes sensoriales son contenido de las guías, no datos medidos.
- Las posiciones aproximadas de electrodos proceden del montaje del backend.
- Los colores y espacios son decisiones del sistema visual.
- Las duraciones y límites de actividad se publican desde el backend.
- El simulador produce datos sintéticos por diseño y se etiqueta visiblemente.

## Alcance de verificación y trabajo pendiente

La suite automática verifica backend, simulación y Cortex mediante mocks; no valida un casco físico ni la usabilidad con participantes. El build de frontend comprueba tipos y empaquetado. La validación también completó 11 comprobaciones de navegador con sesiones aisladas, incluidas móvil, cierre por tiempo y descarte temporal. Consulta TESTING.md para reproducirlas y revisar los casos manuales pendientes.

No se incorporaron diagnósticos, índices de estrés, localización cortical ni nuevas licencias de hardware. Tampoco se convirtió la aplicación local en un servicio multiusuario.

El almacenamiento temporal no es solo memoria. Cerrar abruptamente una pestaña puede dejar una sesión temporal en disco hasta reiniciar el backend. Los mínimos, máximos y desviaciones EEG describen ventanas agregadas, no muestras crudas. La pausa de calma no pausa el registro EEG ni persiste tras recarga.
