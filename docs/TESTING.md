# Pruebas y validación

## Resultados y alcance

| Verificación | Base anterior | Último resultado |
| --- | --- | --- |
| Backend pytest | 66 aprobadas | 76 aprobadas, incluidas las anteriores |
| Modelos frontend | Sin suite propia | 4 aprobadas |
| Navegador Chrome | 11 comprobaciones | 22 aprobadas |
| TypeScript y producción | Correctos | Correctos; incluye comprobación de código sin uso |

La auditoría inicial y recuperación están en [Historial](CHANGELOG.md). Las pruebas usan bases temporales: no se abrió la base de participantes. Las capturas del README proceden de la aplicación con datos sintéticos; no son mockups ni validación de hardware.

## Backend

Desde backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Se conservan test_api, test_simulator, test_emotiv y test_math_limits. test_evolution cubre migración legacy idempotente con datos previos, publicación entre hilos/snapshots y cola acotada, recuperación de escritura, creación simultánea de sesión/fase, adquisición tras desconexión del cliente y contratos NeuroCode. Los límites usan un reloj inyectado; el piloto verifica tarea, fase, intentos, plazo, esfuerzo y CSV sin inventar EEG.

Un primer intento restringido falló por permisos de temporales; con acceso adecuado pasó la suite. La combinación instalada de Starlette/httpx produce una advertencia de deprecación de TestClient.

## Frontend

Desde frontend:

```powershell
npm test
npm run build
```

node:test usa el compilador TypeScript existente para comprobar búfer circular, cortes de señal/origen/unidades, valores originales de sensores y distinción de instrucciones por modelo. No simula React para afirmar pruebas de interfaz. El build comprueba tipos, código sin uso y empaquetado.

Verificado con Python 3.12 y Node 24. En el equipo de desarrollo, nvm no tenía una versión activa; se utilizó un Node instalado sin cambiar la configuración global. Cada integrante debe activar su propio entorno.

El módulo 3D supera 500 kB sin comprimir (aproximadamente 138 kB gzip). Se importa bajo demanda y se mantiene el aviso de Vite; no se eleva el límite para ocultarlo.

## Navegador real

Desde la raíz, con Chrome o Edge instalado:

```powershell
.\backend\.venv\Scripts\python.exe scripts/test_browser.py
```

--basic ejecuta el recorrido original. La suite completa incluye browser_checks.py. Si el gestor de Node no tiene una versión activa, NEUROSYNC_NODE_BIN permite indicar un ejecutable instalado.

El script abre backend, Vite y un navegador oculto con puertos, perfil y SQLite aislados en .tmp/uiqa-*. Cierra todos los procesos que inició y conserva capturas/logs. Usa renderizado de software para verificar WebGL independientemente de la GPU local.

Cobertura:

- Escritorio/móvil de 375 px, filtros, leyenda, calidad deficiente y pérdida/recuperación sin valores ficticios.
- Selección 2D, clic sobre electrodo 3D, controles, inspector compartido, tema y alternativa 2D sin WebGL.
- Tutorial por modelo sin selección automática y bloqueo del inicio real sin completar preparación.
- Navegación sin duplicar fases; pausa/técnica conservadas; matemáticas con Enter repetido, vencimiento, calma y resultados.
- NeuroCode completo con recuperación del catálogo tras bloquear su petición y esfuerzo opcional.
- Historial, interrupción, descarte temporal, desconexión del servidor y ausencia de excepciones JavaScript no controladas.

## Validación pendiente

Cortex está probado con servidor simulado; no se ha validado con casco físico ni con Virtual Brainwear real. Comprobar autorización/licencia de la cuenta universitaria, recepción y unidades, contacto, desconexión física y comodidad de colocación usando [la guía EMOTIV](EMOTIV_SETUP.md).

La automatización no sustituye probar accesibilidad, textos y comodidad con participantes ni validar el catálogo y protocolo de [Investigación](RESEARCH.md).
