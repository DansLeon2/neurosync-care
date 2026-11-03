# Limitaciones Científicas, Metodológicas y Éticas

## 1. Propósito No Médico

**NeuroSync Care** es una plataforma experimental universitaria de biofeedback y autorregulación desarrollada en Cuenca, Ecuador.

- **No es un dispositivo médico** ni un instrumento de diagnóstico clínico.
- **No diagnostica** trastornos de ansiedad, depresión, TDAH, epilepsia ni ninguna condición neurológica o psiquiátrica.
- **No identifica emociones discretas individuales** (como felicidad, tristeza o enojo) a partir del EEG superficial.
- **No observa neuronas individuales ni conexiones sinápticas reales**. El EEG superficial registra sumas de potenciales postsinápticos de grandes poblaciones corticales atenuadas por el cráneo y el cuero cabelludo.

---

## 2. Rigor en la Visualización y el Análisis

1. **Distinción estricta de fuentes**:
   - Todo dato generado por el simulador se etiqueta visiblemente como `DATOS SIMULADOS` y emplea unidades `u.a. (simulado)`.
   - Si en una misma sesión se alternan fuentes de datos, el informe final (`NeuroReport`) muestra una advertencia de fuentes mixtas (`mixed_sources`).
2. **Sin índices clínicos arbitrarios**:
   - No se inventan fórmulas propietarias de "porcentaje de estrés clínico" a partir de combinaciones arbitrarias de Alfa, Beta o Theta.
   - Los indicadores reportados son estadísticas descriptivas directas (media, desviación estándar, mínimo, máximo, cambio absoluto y cambio porcentual intra-sujeto entre fases de la misma sesión).
3. **Sin interpolación de datos perdidos**:
   - Cuando ocurre una desconexión o pérdida de señal (`SIGNAL_LOST`), las ventanas afectadas se contabilizan como muestras faltantes (`n_missing`) y no se rellenan con valores sintéticos.
4. **Seguridad en ejercicios de autorregulación (`NeuroCalma`)**:
   - Ningún ejercicio exige retenciones de aire forzadas ni hiperventilación.
   - Se ofrece una alternativa de **Atención Abierta al Presente** sin foco respiratorio y controles permanentes para pausar o detener la actividad en cualquier momento.



## Precisión de los datos presentados

La interfaz representa potencias por banda entregadas por la fuente, no EEG crudo, una FFT calculada localmente, conexiones neuronales ni áreas corticales medidas. Las posiciones de electrodos son aproximadas.

Los estadísticos de bandas se calculan sobre ventanas agregadas por sensor. Sus mínimos, máximos y desviaciones describen esas medias de ventana, no las muestras originales. Las ventanas parciales conservan su conteo pero actualmente tienen el mismo peso en la estadística descriptiva.

La exactitud aritmética es correctas / operaciones enviadas (incluidas omisiones); la latencia media excluye omisiones. Ninguna de estas métricas evalúa inteligencia ni permite inferir un diagnóstico.

Las sesiones sin autorización de historial también usan SQLite de forma temporal; pueden permanecer en disco hasta descartarlas o reiniciar el backend.
