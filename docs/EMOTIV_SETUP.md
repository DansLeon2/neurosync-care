# Preparación y conexión EMOTIV

## Orden de conexión

Casco → receptor compatible → EMOTIV Launcher/Cortex → backend local → navegador.

Con la configuración predeterminada, Launcher y el backend deben estar en el mismo equipo: Cortex se consulta en `wss://localhost:6868`. [Conexión oficial de Cortex](https://emotiv.gitbook.io/cortex-api/connecting-to-the-cortex-api).

## Lista para la primera conexión

1. Instala [EMOTIV Launcher](https://www.emotiv.com/quick-start-guide-epoc-x), inicia sesión y comprueba que reconoce el casco físico encendido. Para EPOC X, la guía oficial utiliza el receptor USB incluido; el cable de carga no sustituye ese receptor. Ten internet para la autorización de la cuenta.
2. Registra una Cortex App en [tu cuenta EMOTIV](https://account.emotiv.com/my-account/cortex-apps/) y obtén **Client ID y Client Secret**. En una aplicación sin publicar, utiliza en Launcher la cuenta con la que se registró la app. [Registro oficial](https://www.emotiv.com/knowledge-base/register-cortex-app-id-sdk) y [errores de acceso](https://emotiv.gitbook.io/cortex-api/error-codes).
3. Desde la raíz del proyecto crea el archivo local solo si no existe:

   ```powershell
   if (!(Test-Path -LiteralPath backend/.env)) {
       Copy-Item -LiteralPath backend/.env.example -Destination backend/.env
   }
   notepad backend/.env
   ```

   Completa `EMOTIV_CLIENT_ID` y `EMOTIV_CLIENT_SECRET`. `EMOTIV_HEADSET_ID` puede quedar vacío si solo hay un casco del tipo elegido. No uses tu contraseña EMOTIV como Client Secret. No publiques ni compartas este archivo.
4. Inicia backend y frontend en dos terminales siguiendo [Ejecutar](../README.md#ejecutar). Si ya estaban abiertos al editar `.env`, reinicia el backend.
5. Abre `http://localhost:5173` → **Dispositivo** → tarjeta **Casco EMOTIV** → **Conectar**. Aprueba NeuroSync Care en Launcher cuando se solicite. Espera **Recibiendo datos**; consulta el mensaje de conexión si no aparece.
6. Vuelve a **Mi sesión → Nueva sesión**, elige **Casco EMOTIV**, identifica el modelo y completa el asistente. Revisa contactos y valores antes de comenzar; la comodidad y colocación se confirman manualmente.

Si usas un dispositivo virtual creado en Launcher, elige **EMOTIV virtual**, no Casco EMOTIV. Para practicar sin cuenta ni casco, usa el Simulador. No cambies fuente mientras exista una sesión activa.

## Cuenta y licencia

La licencia universitaria debe comprobarse para la cuenta, aplicación y flujos concretos. EMOTIV publica Frequency Band API dentro del acceso Basic para EPOC X; el EEG crudo y las métricas de alta resolución pertenecen al acceso Premium. Consulta los [requisitos vigentes de Cortex](https://emotiv.gitbook.io/cortex-api) antes de adquirir o solicitar algo adicional.

Esta aplicación solicita exclusivamente `pow`, `eq` y `dev`. No envía un identificador de licencia explícito al autorizar. Una suscripción o permiso adicional no activa por sí solo `eeg` o `met` en NeuroSync Care.

## Preparación antes de una sesión real

El asistente aparece dentro de Nueva sesión al elegir una fuente EMOTIV. El usuario debe identificar explícitamente el modelo; no se deduce una instrucción universal de la posición de un electrodo.

| Modelo | Diferencia que debe respetarse | Fuente del contenido |
| --- | --- | --- |
| EPOC X | Fieltros y preparación con la solución indicada por el fabricante; ajuste propio del modelo | [Guía EPOC X](https://www.emotiv.com/quick-start-guide-epoc-x) |
| EPOC+ | Preparación y orientación de EPOC+; no trasladar el ajuste de diadema de EPOC X | [Guía EPOC+](https://www.emotiv.com/quick-start-guide-epoc-plus) |
| Insight | Sensores de polímero semiseco y procedimiento/líquido específicos; no fieltros EPOC | [Guía Insight](https://www.emotiv.com/quick-start-guide-insight) |
| EPOC original u otro | Consultar su manual específico; no se dan instrucciones físicas de otro modelo | [Manuales EMOTIV](https://emotiv.gitbook.io/emotiv-home) |

El tutorial cubre preparación, electrodos, colocación, conexión, calidad y comodidad. Las ilustraciones son SVG propios. No se incluyen recetas, fotografías oficiales copiadas ni maniobras no verificadas.

Las primeras revisiones y la comodidad se confirman manualmente. La conexión y llegada de potencia se comprueban desde el software, exclusivamente para la fuente seleccionada. Se muestran los contactos recibidos; un valor desconocido no se considera bueno. Un contacto menor que 3/4 se señala para revisión como criterio operativo, sin certificar validez científica. La persona debe confirmar que revisó las limitaciones de calidad.

El asistente también se puede consultar desde Dispositivo. En simulación se explica que no hace falta casco. En un dispositivo virtual, las lecturas son del entorno virtual y no demuestran colocación física.

## Diagnóstico

| Estado | Acción |
| --- | --- |
| CREDENTIALS_MISSING / CREDENTIALS_INVALID | Revisar Client ID/Secret de la Cortex App y reiniciar backend |
| CORTEX_NOT_INSTALLED / CORTEX_UNAVAILABLE | Instalar/abrir Launcher en este mismo equipo e iniciar sesión |
| AUTHORIZATION_PENDING | Aprobar la aplicación en Launcher |
| DEVICE_NOT_FOUND | Revisar encendido, receptor y visibilidad del casco en Launcher |
| STREAM_NOT_AUTHORIZED | Revisar los permisos del flujo pow para esa cuenta/aplicación |
| DEVICE_DISCONNECTED / SIGNAL_LOST | Revisar encendido, receptor y contacto; los huecos no se rellenan |
| COMMUNICATION_ERROR | Leer el mensaje, comprobar Launcher y volver a conectar antes de iniciar sesión |

No se desactiva TLS para resolver errores. La batería, los contactos y los datos no se inventan cuando faltan. La conexión física y la adecuación de estas instrucciones al equipo universitario deben validarse con el responsable del dispositivo. El adaptador se comprueba automáticamente contra Cortex simulado.

## Detalles del adaptador

`backend/app/acquisition/emotiv.py` implementa JSON-RPC seguro: verificación TLS con la CA oficial → `getCortexInfo` → `hasAccessRight`/`requestAccess` → `authorize` → `queryHeadsets` → `controlDevice(connect)` si procede → `createSession(open)` → `subscribe`. Distingue `REAL_EMOTIV` de `VIRTUAL_DEVICE` según el tipo de casco; no simula una conexión física ausente.

`emotiv_normalizer.py` interpreta las columnas `cols` devueltas por la suscripción, sin índices fijos. Soporta montajes de 14 canales y de cinco canales en sus pruebas.

| Flujo | Datos utilizados | Frecuencia documentada |
| --- | --- | --- |
| `pow` | Potencia por sensor de theta, alpha, betaL, betaH y gamma; `µV²/Hz` | 8 Hz |
| `eq` | Calidad EEG por sensor y global, calidad de muestreo | 2 Hz |
| `dev` | Batería, señal inalámbrica y contacto | 2 Hz |
| `eeg`, `met` | No se solicitan: decisión de alcance del proyecto | — |

`pow` contiene potencia absoluta calculada por Cortex con los dos segundos anteriores de EEG; la gráfica no es un osciloscopio de onda cruda. [Formato oficial de las muestras](https://emotiv.gitbook.io/cortex-api/data-subscription/data-sample-object).

Los secretos se leen exclusivamente en `Settings` del backend, desde variables de entorno o `backend/.env`. Se conserva lectura del `.env` de la raíz por compatibilidad; las configuraciones nuevas deben usar el único ejemplo en backend. Ningún secreto se envía al frontend.

La implementación asíncrona, estados, normalización y pruebas son propios. Los patrones de protocolo y la CA proceden del [ejemplo oficial de EMOTIV](https://github.com/Emotiv/cortex-example); se conserva su [aviso MIT](../backend/app/acquisition/certs/EMOTIV_LICENSE_MIT.txt) junto al certificado. [Pruebas y alcance de validación](TESTING.md).
