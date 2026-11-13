# Pruebas y validación

## Base de comparación

Antes de modificar el código: 66 pruebas pytest, build de producción y 11 comprobaciones de navegador aprobadas. Capturas originales en la carpeta local ignorada .tmp/uiqa-c470d7f6. Un intento inicial restringido de pytest falló por permisos; al ejecutar con acceso a temporales pasó completa.

El equipo tiene nvm sin versión activa. Se usó un ejecutable Node instalado para la comprobación local, sin cambiar la configuración global. No es una dependencia de rutas personales dentro del proyecto.

## Backend

Desde backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

La suite usa bases temporales; no apunta a la base de participantes. Conserva test_api, test_simulator, test_emotiv y test_math_limits. test_evolution añade migración legacy idempotente, publicación entre hilos y snapshots, cola acotada, recuperación de escritura, creación simultánea de sesiones/fases, continuación de adquisición tras desconexión del cliente y contratos NeuroCode.

Las pruebas de tiempo usan reloj inyectado para los límites. El piloto valida tarea, fase, corrección, número de intentos, esfuerzo opcional y exportación sin fabricar datos EEG.

La versión instalada de Starlette/httpx produce una advertencia de deprecación de TestClient. No se reemplazó esa dependencia indirecta como parte de esta intervención.

## Frontend

Desde frontend:

```powershell
npm test
npm run build
```

node:test usa el compilador TypeScript ya instalado para probar modelos puros: búfer, cortes de señal/origen/unidades, valores de sensor sin relleno y distinción de instrucciones según el modelo. No imita React para afirmar pruebas de interfaz.

El build verifica tipos y empaquetado. El chunk 3D supera 500 kB sin comprimir y se carga bajo demanda; no se oculta esa advertencia elevando artificialmente el límite.

## Navegador real

Desde la raíz, con Chrome o Edge instalado:

```powershell
.\backend\.venv\Scripts\python.exe scripts/test_browser.py
```

Con --basic se ejecuta el recorrido original. Por defecto se incluyen las comprobaciones ampliadas de browser_checks.py. El ejecutable de Node puede indicarse con NEUROSYNC_NODE_BIN cuando un gestor local no tiene una versión activa.

La prueba arranca Vite, backend y un perfil de navegador aislados en puertos libres, con SQLite dentro de .tmp/uiqa-*. Cierra los procesos que inició y conserva capturas y logs para revisión. Chrome usa renderizado de software en esta prueba para que 3D sea verificable sin depender de la GPU local.

Cobertura ampliada:
- Escritorio y móvil de 375 px sin desbordamiento.
- Filtros de banda, sensor, ventana y leyenda.
- Calidad deficiente y pérdida/recuperación sin valores inventados.
- Selección en 2D y clic real sobre un electrodo 3D, zoom, orientación y selección compartida.
- Tema alternativo y preparación por modelo sin selección automática.
- Fuente real bloqueada hasta completar preparación; sin confirmar hardware inexistente.
- Navegación sin fases duplicadas; guía pausada/técnica conservadas.
- Flujo matemático, Enter repetido, vencimiento, calma y resultado.
- NeuroCode completo con reintento tras fallo de catálogo, esfuerzo opcional y exportación disponible.
- Descarte temporal, historial de interrupción y desconexión del servidor.
- WebGL indisponible: aviso y vista 2D.
- Ausencia de excepciones JavaScript no controladas.

## Comprobaciones manuales pendientes

La automatización no sustituye probar el casco universitario ni observar usabilidad con participantes. Revisar colocación, higiene y adecuación por modelo con el responsable del equipo. Probar autorización/licencia reales, desconexión física, variación de contacto y confirmación de unidades.

Verificar con participantes accesibilidad, textos y comodidad; validar el protocolo y el catálogo de tareas antes de investigar asociaciones. El piloto no estima productividad ni constituye un instrumento validado de estrés.

## Resultado de esta intervención

La ejecución final se registra en CHANGELOG.md y en el informe de entrega. Las capturas del README proceden de sesiones simuladas reales de la app; no son mockups ni validación de hardware.
