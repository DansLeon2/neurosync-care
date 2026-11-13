# Historial y auditoría

## Consolidación de documentación y código

La documentación pasa de doce a seis archivos Markdown. El README contiene el índice y las instrucciones de instalación; cada guía conserva una responsabilidad:

| Contenido anterior | Ubicación actual |
| --- | --- |
| Índice separado | [README](../README.md) |
| Preparación e integración EMOTIV | [EMOTIV_SETUP](EMOTIV_SETUP.md) |
| Protocolo, NeuroCode y limitaciones científicas | [RESEARCH](RESEARCH.md) |
| Auditorías e historial de la primera simplificación | Este archivo; versiones completas conservadas en Git |
| Detalles técnicos, uso y comprobaciones | [Arquitectura](ARCHITECTURE.md), [usuario](USER_GUIDE.md) y [pruebas](TESTING.md) |

Se retiraron los siete documentos sustituidos, se actualizaron enlaces y comentarios del adaptador, y se unificó la configuración de ejemplo en backend/.env.example. No se modificaron los archivos privados .env existentes ni la lectura compatible de configuraciones anteriores.

En frontend se eliminaron ocho importaciones sin uso, una reexportación obsoleta y el campo channels vacío de la historia visual. TypeScript ahora comprueba variables y parámetros sin utilizar. La revisión del grafo de importaciones encontró los 40 módulos de código accesibles desde main.tsx; no se eliminaron módulos funcionales.

## Evolución interactiva — 423beaa

Antes de modificar código se comprobó una rama limpia y se creó checkpoint/pre-evolution-20261112. La [validación](TESTING.md) conserva la comparación inicial y los resultados.

| Riesgo detectado | Severidad | Solución |
| --- | --- | --- |
| Publicación en colas asyncio desde hilos; ventanas retiradas antes del commit | Alta | Entrega en el loop propietario, snapshots y retención de ventanas ante fallo |
| Mutaciones simultáneas y tareas WebSocket sin esperar su cancelación | Alta/media | Serialización dentro del proceso y limpieza sin detener adquisición |
| Desmontaje de la guía al navegar; render global por muestra | Media | Recorrido persistente, suscriptores locales y búfer acotado |
| Gráficas sin ejes/inspector completo; preparación sin distinción por modelo | Media | Filtros, huecos, inspector común y asistente adaptable |
| Código sin consumidores y documentos repetidos | Baja | Retirada de SelfReportModal y consolidación posterior |

Se incorporaron el explorador 3D con alternativa 2D, el piloto controlado NeuroCode, autoevaluación opcional de esfuerzo y migraciones aditivas. Se conservaron React 18, FastAPI, SQLite, el simulador, el adaptador Cortex, los temas y las gráficas de informes. Three.js directo evita otro reconciliador y modelos anatómicos externos.

Vite 5 se actualizó a 6.4.6 y su plugin React a 4.7.0 para corregir dos alertas detectadas; npm audit terminó sin vulnerabilidades. Los avisos de tamaño del módulo 3D y deprecación de TestClient están registrados en [Pruebas](TESTING.md).

## Primera simplificación y mejoras previas

La primera revisión sustituyó pantallas competidoras por el recorrido Preparar → Actividad → Calma → Resultados. Corrigió el límite de veinte operaciones, vencimiento comprobado al emitir y corregir, vinculación con la fase original, pregunta pendiente reutilizable y concurrencia de respuestas. Unificó exactitud incluyendo omisiones y excluyó estas de la latencia.

También eliminó comodidad inventada, consentimiento/demostración preseleccionados, ondas sintéticas presentadas como medición y etiquetas de localización cortical. Conservó guías sin retenciones, movimiento reducido, teclado accesible, foco modal y cierre por Escape. Detener marca ABORTED; cambiar fuente durante una sesión queda bloqueado. Después se añadieron el tema alternativo y gráficas de informes.

## Capturas verificadas

Imágenes de la app ejecutada con datos exclusivamente sintéticos: [antes](screenshots/session-before.png), [actividad actual](screenshots/session.png), [explorador 3D](screenshots/explorer.png), [preparación](screenshots/preparation.png) y [NeuroCode](screenshots/neurocode.png).

## Recuperación

El historial completo de los documentos eliminados permanece en Git. Por ejemplo:

```bash
git show 423beaa:docs/AUDIT_2026-11.md
git show checkpoint/pre-evolution-20261112:README.md
git diff checkpoint/pre-evolution-20261112..HEAD
```

Recuperar código no revierte SQLite. La copia de seguridad y la compatibilidad de migraciones se explican en [Arquitectura](ARCHITECTURE.md); el estado de hardware y el trabajo futuro, en [EMOTIV](EMOTIV_SETUP.md) e [Investigación](RESEARCH.md).
