# NeuroSync Care

Plataforma experimental local para observar potencia EEG, realizar una actividad aritmética y practicar una pausa guiada. No realiza diagnósticos ni identifica emociones.

## El recorrido en una frase

**Preparar → Actividad → Calma → Resultados.**

1. En **Mi sesión**, elige simulador o EMOTIV, decide si guardar la sesión y, opcionalmente, indica tu tensión inicial.
2. La referencia inicial comienza al preparar la sesión. Al terminar, pulsa **Comenzar operaciones** y elige dificultad.
3. Resuelve hasta **20 operaciones o 120 segundos**, lo que ocurra primero. Puedes omitir o terminar antes. Registra después tu tensión percibida.
4. Comienza la pausa de calma: respiración 4–6, 4–4 o atención al entorno. Puedes pausar la guía o terminar antes.
5. Registra tu tensión final y consulta el resumen. Las comparaciones técnicas y las exportaciones están en Resultados.

La modalidad de demostración usa 8 s de referencia, 8 s de operaciones y 10 s de calma. La duración estándar es de 2 + 2 + 3 minutos, más el tiempo de responder y continuar. Las definiciones se publican en `GET /api/protocol`.

**Detener sesión** produce un resultado interrumpido (`ABORTED`), no una sesión completada.

## Navegación

- **Mi sesión:** recorrido guiado en una sola pantalla.
- **Resultados:** resumen, historial autorizado, comparación de fases, CSV e impresión.
- **Dispositivo:** conexión, estado y ajustes técnicos plegados.
- **Herramientas:** sensores y prácticas independientes sin registro. Durante una sesión, las actividades se realizan desde Mi sesión.

Las gráficas muestran potencia por banda recibida, no una onda EEG cruda ni una FFT calculada por esta aplicación. Los datos ausentes se muestran como ausentes. El simulador siempre se identifica como tal.

## Ejecutar en Windows

Requisitos: Python 3.11 o posterior compatible con las dependencias, Node.js y npm. Ejecuta estos comandos desde la raíz.

Preparación del backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Terminal 1:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 (la primera vez, ejecuta `npm ci`):

```powershell
cd frontend
npm ci
npm run dev
```

Abre http://localhost:5173. API interactiva: http://127.0.0.1:8000/docs. Al abrir la app no se conecta automáticamente ninguna fuente; el simulador se inicia al elegirlo para una sesión o desde Dispositivo.

Para EMOTIV, copia `backend/.env.example` a `backend/.env` y configura tus credenciales. No se necesitan para el simulador. Consulta [la integración](docs/EMOTIV_INTEGRATION.md).

## Datos y almacenamiento

La aplicación es local, de un único proceso y para una sesión activa a la vez. No incluye autenticación multiusuario. Conserva la API en la interfaz local.

La autorización de historial empieza desmarcada. Una sesión temporal también utiliza SQLite mientras está en curso y al mostrar su resultado; queda fuera del historial. El cliente solicita su descarte al salir de Resultados y el backend purga sesiones temporales al reiniciar. Cerrar la pestaña o perder la red puede dejar esos datos temporales en disco hasta el próximo arranque. No equivale a un modo exclusivamente en memoria.

Los CSV son copias descargadas que no se eliminan al borrar la sesión. No se solicitan identificadores personales, pero las mediciones y autoevaluaciones siguen siendo datos del participante.

## Verificar

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd frontend
npm run build
```

Consulta los casos de prueba manual y los límites de verificación en [TESTING.md](docs/TESTING.md).

## Documentación

- [Arquitectura y flujo](docs/ARCHITECTURE.md)
- [Auditoría y decisiones de simplificación](docs/PROJECT_REVIEW.md)
- [Integración EMOTIV](docs/EMOTIV_INTEGRATION.md)
- [Límites científicos y metodológicos](docs/SCIENTIFIC_LIMITATIONS.md)
- [Pruebas](docs/TESTING.md)
