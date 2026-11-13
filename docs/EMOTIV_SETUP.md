# Preparación y conexión EMOTIV

## Orden de conexión

Casco → receptor compatible → EMOTIV Launcher/Cortex → backend local → navegador.

Con la configuración predeterminada, Launcher y el backend deben estar en el mismo equipo: Cortex se consulta en wss://localhost:6868. Inicia sesión con la cuenta autorizada para la aplicación.

Registra una Cortex App y configura Client ID y Client Secret en backend/.env a partir del ejemplo. No publiques ese archivo. El ID del casco es opcional si solo hay uno conectado. Reinicia el backend después de editar la configuración y aprueba la aplicación en Launcher cuando se solicite.

En Dispositivo elige Casco EMOTIV, o Dispositivo virtual si realmente has creado uno en Launcher. La integración actual solicita pow, eq y dev; una licencia adicional no habilita automáticamente otros flujos en este software.

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
| CREDENTIALS_MISSING / INVALID | Revisar la configuración local y reiniciar backend |
| CORTEX_UNAVAILABLE | Abrir Launcher e iniciar sesión |
| AUTHORIZATION_PENDING | Aprobar la aplicación en Launcher |
| DEVICE_NOT_FOUND | Revisar encendido, receptor y visibilidad del casco en Launcher |
| STREAM_NOT_AUTHORIZED | Revisar los permisos del flujo pow para esa cuenta/aplicación |

No se desactiva TLS para resolver errores. La batería, los contactos y los datos no se inventan cuando faltan. La conexión física y la adecuación de estas instrucciones al equipo universitario deben validarse con el responsable del dispositivo. El adaptador se comprueba automáticamente contra Cortex simulado.
