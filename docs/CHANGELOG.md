# Evolución de NeuroSync Care · noviembre de 2026

## Punto de partida y recuperación

La auditoría se realizó antes de modificar código: [hallazgos y riesgos](AUDIT_2026-11.md). La rama inicial estaba limpia y superó 66 pruebas de backend, compilación y 11 comprobaciones de navegador. Se conservaron el tema claro/oscuro, las gráficas de informes y la secuencia de sesión guiada.

El estado inicial está etiquetado como `checkpoint/pre-evolution-20261112`; la implementación está en `feat/interactive-eeg-lab`. Para revisar el código original sin alterar esta rama:

```bash
git show checkpoint/pre-evolution-20261112:README.md
git diff checkpoint/pre-evolution-20261112..feat/interactive-eeg-lab
```

La etiqueta permite recuperar código; no deshace cambios de SQLite. Antes de actualizar un equipo con datos de investigación, conservar una copia de la base con el servidor detenido. No abrir una base con actividades CODING usando una versión antigua que desconoce ese tipo.

## Implementado

| Área | Cambio y archivos principales |
| --- | --- |
| Telemetría | `features/telemetry`: búfer circular de 1024 entradas, suscripciones locales, una conexión WebSocket y actualización visual agrupada; filtros, ejes, unidades, tooltip, leyenda y cortes de señal. `useNeuroStream` conserva el estado de sesión y conexión. |
| Explorador | `features/neuromap` y `NeuroMapPage`: modelo común de sensores, inspector original y vistas 2D/3D; selección con ratón/teclado, giro, zoom, restablecimiento y ocultación. Three.js se importa al solicitar 3D y libera sus recursos al desmontarse. |
| Preparación | `features/session/DevicePreparation` y `preparationContent`: seis pasos por modelo sin elección automática, ilustración propia, datos de contacto recibidos y comprobaciones manuales diferenciadas. Integrado en `SessionStartModal` y disponible en Dispositivo. |
| Flujo | `useGuidedSession`, `DashboardPage` y `App`: el recorrido permanece montado al navegar; no reinicia preguntas, fases ni pausa de la guía. El reloj de fase procede del backend. Se conservan consentimiento y demostración desmarcados. |
| Backend | `hub.py`: publicación en el loop propietario y mensajes copiados; `recorder.py`: retiro de ventanas después del commit y conservación ante fallo; `websocket.py`: cancelación y espera de tareas sin detener adquisición. `session_service.py`: serialización de mutaciones dentro del proceso. |
| NeuroCode | Registro de actividades, catálogo de dos tareas, `coding_service.py`, esquema y tabla de respuestas, `CodingActivity` y reporte/CSV. Corrección determinista, hasta tres intentos y plazo del servidor; esfuerzo subjetivo opcional. El catálogo se carga al comenzar la actividad y permite reintentar tras un fallo de conexión. |
| Persistencia | `database/migrations.py`: migración aditiva e idempotente para `activity_kind` y `effort`; tabla `coding_answers` nueva. Las sesiones anteriores conservan identificadores y datos, con actividad MATH. |
| Mantenimiento | Configuración HTTP/WS centralizada, contratos tipados, eliminación de `SelfReportModal` sin consumidores, documentación por responsabilidad y pruebas adicionales. |

React 18, FastAPI, SQLite y el adaptador Cortex se mantienen. Se añade Three.js directo, sin otro reconciliador React ni recursos anatómicos externos. Vite pasa de 5 a 6.4.6 y su plugin React a 4.7.0 para corregir dos alertas de dependencias detectadas durante la revisión; `npm audit` final informó **0 vulnerabilidades**. No se aplicó una actualización forzada a otra arquitectura.

## Verificación ejecutada

| Comprobación | Resultado |
| --- | --- |
| Backend completo | **76 aprobadas**, incluidas las 66 originales; una advertencia de deprecación Starlette/httpx. |
| Modelos puros de frontend | **4 aprobadas**: búfer, huecos/cambio de fuente/unidades, sensor y tutorial por modelo. |
| TypeScript y producción | Correctos con Node 24; entrada JS de 248 kB y 78 kB gzip. |
| Navegador Chrome | **22 comprobaciones aprobadas**, con backend y base aislados; sin excepciones JavaScript no controladas. |
| Migración y persistencia | Verificadas con datos legacy sintéticos y ejecución repetida; no se utilizó la base de participantes. |

El recorrido de navegador verifica escritorio y móvil de 375 px, filtros, calidad deficiente, pérdida/recuperación, selección real de un electrodo 3D, controles, inspector compartido, tema alternativo, tutorial por modelo, navegación durante actividad y pausa, flujo matemático completo, límite temporal, Enter repetido, historial, descarte temporal, NeuroCode completo con recuperación del catálogo tras bloquear su petición y alternativa 2D cuando WebGL falla. [Cómo repetirlo](TESTING.md).

Los resultados finales locales están en `.tmp/final-pytest.log` y `.tmp/final-browser.log`; las capturas completas de esa ejecución, en `.tmp/uiqa-4f99f03a`. Son artefactos ignorados por Git. Las siguientes imágenes se conservan como documentación y contienen exclusivamente datos sintéticos.

## Revisión visual

Se abrieron las capturas de la actividad, el explorador 3D, el tutorial y la alternativa móvil. También se revisó el piloto NeuroCode durante su implementación. Las capturas muestran la aplicación ejecutada, no diseños propuestos.

- [Sesión antes de esta intervención](screenshots/session-before.png).
- [Actividad y gráfica después](screenshots/session.png).
- [Explorador 3D después](screenshots/explorer.png).
- [Preparación por modelo](screenshots/preparation.png).
- [Piloto de lectura de código](screenshots/neurocode.png).

## Pendiente de dispositivo real

La integración Cortex conserva sus contratos y supera las pruebas con servidor simulado. No se conectó un casco físico en esta intervención. Falta comprobar con el equipo universitario la autorización y licencia, el modelo concreto, la recepción y unidades del flujo `pow`, calidad/contacto, desconexión física y comodidad de colocación.

La geometría 3D es ilustrativa y las posiciones de electrodos son aproximadas. Sus colores representan valores de sensores; no localización neuronal. Su módulo opcional pesa 552 kB sin comprimir y 138 kB gzip; Vite avisa al superar 500 kB. Se carga bajo demanda y se conserva el aviso.

La pausa de la guía se conserva al navegar dentro de la aplicación; una recarga completa reconstruye el estado del servidor y no persiste esa pausa local. La API continúa diseñada para un único proceso local, sin autenticación multiusuario.

## Propuesto para el futuro

La [propuesta NeuroCode](NEUROCODE_PROPOSAL.md) separa el piloto implementado de tareas con editor, marcas de estímulo, reproducción sincronizada y análisis de asociaciones. No se implementaron ejecución arbitraria, seguimiento de IDE, vigilancia, puntuación de productividad ni un clasificador de estrés. El catálogo y el protocolo todavía necesitan validación académica y pruebas de usabilidad con participantes.
