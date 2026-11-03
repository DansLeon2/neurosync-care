# Pruebas y validación

## Backend

Desde backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas usan SQLite temporal. No deben apuntar a la base de participantes.

- test_api.py: sesiones, consentimiento, fases, autoevaluaciones, historial, comparación y CSV.
- test_simulator.py: señales sintéticas reproducibles, escenarios y pérdida de señal.
- test_emotiv.py: normalización y comunicación contra Cortex simulado; no hardware físico.
- test_math_limits.py: plazo de actividad, caducidad al responder, fase de origen, máximo de preguntas, acotación de entrada, duplicados y concurrencia local.

Los casos temporales nuevos usan un reloj inyectado; no requieren esperar minutos para comprobar caducidad.

## Frontend

Desde frontend:

```powershell
npm run build
```

Comprueba TypeScript y el empaquetado de Vite. No equivale a una prueba visual ni comprueba por sí mismo el flujo en un navegador.

## Comprobación automática en navegador (Windows)

Desde la raíz, con Chrome o Edge instalado:

```powershell
.\backend\.venv\Scripts\python.exe scripts/test_browser.py
```

El script utiliza el cliente WebSocket instalado con las dependencias del backend. Inicia backend, Vite y Chrome/Edge sin ventana, en puertos libres, con SQLite y perfil de navegador aislados dentro de .tmp/uiqa-*. Al terminar cierra los procesos que inició. No usa la base de sesiones del proyecto.

Comprueba escritorio y móvil de 375 px sin desbordamiento, consentimiento desmarcado, ausencia de respuestas iniciales inventadas, flujo guiado, Enter repetido, vencimiento de matemáticas, pausa de calma, descarte temporal, sesión guardada interrumpida y desconexión del servidor. Guarda capturas locales y falla ante excepciones de JavaScript.

## Recorridos manuales

1. Abrir sin backend: debe aparecer un error recuperable con Reintentar, no datos de relleno.
2. Preparar una sesión: consentimiento desmarcado, duración estándar y tensión inicial opcional sin respuesta preseleccionada.
3. Usar simulador y demostración: completar referencia, operaciones, autoevaluación, calma y evaluación final desde Mi sesión.
4. Dejar transcurrir el tiempo matemático: entrada bloqueada, sin pregunta nueva y continuación a autoevaluación.
5. Ronda estándar: llegar a 20 respuestas, incluidas omisiones; la fase termina.
6. Responder con Enter repetido: una corrección por pregunta. Comprobar pregunta sin “= ?” duplicado.
7. Intentar respuesta vacía, decimal y número de más de cuatro cifras. Omitir debe ser una acción explícita.
8. Recargar durante operaciones: recuperar el plazo de la fase y las respuestas ya registradas.
9. Perder conexión: borrar la última telemetría, mostrar aviso, recuperar sin fabricar señal.
10. Durante sesión, intentar cambiar fuente o entrar a prácticas: fuente bloqueada y regreso a Mi sesión.
11. Detener desde la cabecera: resultado interrumpido.
12. Sin autorización de historial: ver/exportar resultado temporal, salir de Resultados y verificar que la sesión se descartó.
13. Con autorización: reiniciar y comprobar historial, CSV e impresión.
14. Calma: probar pausa, reanudación y alternativa de atención al entorno. La interfaz debe aclarar que el EEG continúa durante la pausa de guía.
15. Probar móvil de 360 px y escritorio; recorrer con Tab, Escape y preferencia de movimiento reducido.

## Resultado de la revisión

La ejecución tras los cambios completó **66 pruebas de backend**, el build de producción del frontend y **11 comprobaciones en navegador**. Se inspeccionaron capturas de escritorio, móvil, operaciones y resultados. La suite emite una advertencia de deprecación de la combinación Starlette/httpx instalada; no impide las pruebas.

## Límites

Los mocks no validan credenciales universitarias, licencias de flujos ni compatibilidad de un casco real. Las fases solo se cierran automáticamente mientras el cliente guiado está ejecutándose; la API siempre impide respuestas matemáticas tardías.

El proceso debe ejecutarse con un solo worker: las preguntas pendientes y el bloqueo son locales a ese proceso.
