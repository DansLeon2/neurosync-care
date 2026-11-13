# Guía de usuario

## Empezar sin equipo

Inicia backend y frontend como explica el README. Abre Mi sesión → Nueva sesión → Simulador. No necesitas cuenta EMOTIV, licencia ni datos de ejemplo descargados. El backend genera señales sintéticas y la interfaz las etiqueta.

Elige Operaciones o Lectura de código (piloto). El guardado en historial empieza desmarcado; las respuestas iniciales no se preseleccionan. La demostración rápida solo cambia las duraciones y también empieza desmarcada.

## Una experiencia continua

1. Preparar: fuente, actividad, autorización de guardado y tensión inicial opcional.
2. Referencia: reposo con contador basado en la fase del servidor.
3. Actividad: operaciones o una tarea controlada de lectura de código.
4. Autoevaluación: tensión y, opcionalmente, dificultad, esfuerzo y comodidad.
5. Calma: guía 4–6, 4–4 o atención al entorno.
6. Evaluación final y resultados.

Estas etapas siguen agrupadas en Preparar → Actividad → Calma → Resultados. Cambiar a Explorador o Dispositivo no crea otra sesión ni reinicia la fase. El botón Detener sesión genera un resultado interrumpido, no completado.

La pausa de calma afecta a la guía, no al registro EEG. La pausa y la técnica se conservan durante navegación; una recarga completa recupera la fase desde el servidor pero no conserva esa pausa local.

## Señal en vivo

El panel junto al ejercicio distingue fuente, conexión y calidad general. Puedes elegir banda, sensor o media entre sensores y una ventana de 5, 15, 30 o 60 segundos. La leyenda permite superponer bandas; la banda principal permanece activa.

El cursor muestra valor y hora. También puedes enfocar la gráfica y usar las flechas. Los ejes muestran tiempo y unidades. Los huecos no se rellenan. Que un sensor no tenga valor no significa potencia cero.

Las pestañas Evolución, Sensores y Eventos separan el detalle. El flujo pow es potencia por bandas: no una onda EEG cruda ni una FFT completa. La calidad general tampoco es un porcentaje de estrés.

## Explorador 2D y 3D

Selecciona un electrodo con clic o con el selector accesible. Ambas vistas usan el mismo inspector. Puedes cambiar banda, colorear por potencia o calidad, ocultar sensores y fijar la escala de color actual.

En automático, los colores de potencia se normalizan entre cero y el máximo actual del montaje: un color puede cambiar porque cambió la escala. Para comparar colores entre instantes, fija la escala y consulta siempre los valores originales. Gris significa sin dato.

En 3D, arrastra para girar, usa la rueda/pellizco para acercar, o los botones de zoom y restablecimiento. Con el lienzo enfocado, las flechas giran o cambian la distancia. El render ocurre cuando cambian datos, cámara o tamaño; no hay una animación neuronal permanente.

Si WebGL falla, aparece un mensaje y vuelve la vista 2D. El cerebro interior y la cabeza son ilustraciones propias, no anatomía individual ni localización de fuentes cerebrales.

## Resultados y datos

El informe conserva las gráficas de fases, evolución y tensión subjetiva. Los valores EEG, las respuestas y las autoevaluaciones están separados. NeuroCode añade intentos, tareas resueltas/no resueltas y tiempo desde inicio de fase; no mide productividad.

Puedes imprimir y descargar los CSV. Una sesión temporal queda fuera del historial; salir de Resultados solicita su descarte. Consulta [la política de retención y los límites científicos](RESEARCH.md) antes de registrar participantes o compartir resultados.

## Si no hay señal

Revisa primero que ambos procesos estén abiertos y que la fuente elegida corresponda al equipo disponible. En Dispositivo se muestra el mensaje de Cortex. Durante una sesión, la fuente está bloqueada para evitar mezclar orígenes. [Conexión y preparación](EMOTIV_SETUP.md).
