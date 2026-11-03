# Integración con EMOTIV Cortex API v2

## 1. Fuentes Oficiales Consultadas

El adaptador `EmotivCortexSource` (`backend/app/acquisition/emotiv.py`) y su normalizador (`backend/app/acquisition/emotiv_normalizer.py`) fueron diseñados siguiendo la especificación oficial de **EMOTIV Cortex v2**:

- Repositorio oficial de referencia: `https://github.com/Emotiv/cortex-example` (`python/cortex.py`, `python/sub_data.py`, `certificates/rootCA.pem`).
- Documentación de conexión JSON-RPC: `https://emotiv.gitbook.io/cortex-api/connecting-to-the-cortex-api`
- Suscripción y formato de muestras: `https://emotiv.gitbook.io/cortex-api/data-subscription/data-sample-object`
- Dispositivos virtuales (Virtual Brainwear®): `https://emotiv.gitbook.io/emotiv-launcher/devices-setting-up-virtual-brainwear-r/creating-a-virtual-brainwear-device`

---

## 2. Flujo de Conexión JSON-RPC (`wss://localhost:6868`)

Cuando el usuario selecciona `VIRTUAL_DEVICE` o `REAL_EMOTIV`, `EmotivCortexSource` ejecuta la siguiente secuencia:

1. **Verificación TLS**: Construye un contexto SSL utilizando el certificado raíz oficial de EMOTIV almacenado en `backend/app/acquisition/certs/emotiv_rootCA.pem`.
2. **`getCortexInfo`**: Verifica que el servicio EMOTIV Launcher / Cortex esté activo localmente.
3. **`requestAccess`**: Solicita aprobación del usuario en EMOTIV Launcher utilizando `EMOTIV_CLIENT_ID` y `EMOTIV_CLIENT_SECRET` (leídos exclusivamente desde `backend/.env`).
4. **`authorize`**: Obtiene el `cortexToken` de sesión.
5. **`queryHeadsets`**: Descubre los cascos conectados y filtra según el modo seleccionado:
   - `VIRTUAL_DEVICE`: prioriza dispositivos con `"isVirtual": true`.
   - `REAL_EMOTIV`: prioriza dispositivos físicos (`"isVirtual": false`).
6. **`controlDevice` (`command: "connect"`)**: Conecta el casco si se encuentra en estado `discovered`.
7. **`createSession` (`status: "open"`)**: Abre la sesión de adquisición en Cortex.
8. **`subscribe` (`streams: ["dev", "eq", "pow"]`)**:
   - Registra las listas dinámicas `cols` devueltas en el resultado de `subscribe` para parsear cada muestra sin depender de índices fijos.

---

## 3. Restricciones de Licencia y Flujos Soportados

| Flujo Cortex | Frecuencia | Estado en NeuroSync Care | Motivo |
| :--- | :--- | :--- | :--- |
| `pow` | 8 Hz | **Activo** | Potencias espectrales por banda (`theta`, `alpha`, `betaL`, `betaH`, `gamma`) autorizadas en acceso estándar. |
| `eq` | 2 Hz | **Activo** | Calidad de señal EEG y calidad por electrodo. |
| `dev` | 2 Hz | **Activo** | Nivel de batería, fuerza de señal inalámbrica y calidad de contacto (`CQ`). |
| `met` | 0.1 Hz | **Deshabilitado por defecto** | Restringido para uso educativo/investigación según políticas de EMOTIV. |
| `eeg` | 128/256 Hz | **Deshabilitado** | Requiere licencia PRO/Premium de acceso a EEG crudo. |

---

## 4. Qué está probado hoy y qué requiere el dispositivo físico

- **Probado mediante pruebas automatizadas (`backend/tests/test_emotiv.py`)**:
  - Parsers dinámicos de columnas para `pow`, `eq` y `dev` tanto en layouts de 14 canales (EPOC X) como de 5 canales (Insight).
  - Flujo completo JSON-RPC contra un servidor Mock Cortex WebSocket (`getCortexInfo` -> `requestAccess` -> `authorize` -> `queryHeadsets` -> `createSession` -> `subscribe`).
  - Manejo limpio de errores: credenciales faltantes (`CREDENTIALS_MISSING`), servicio Cortex apagado (`CORTEX_UNAVAILABLE`), autorización pendiente (`AUTHORIZATION_PENDING`), dispositivo no encontrado (`DEVICE_NOT_FOUND`) y flujo no autorizado (`STREAM_NOT_AUTHORIZED`).
- **Pendiente de validación con hardware físico universitario**:
  - Prueba en vivo con el casco EMOTIV EPOC / EPOC X físico del club de Biomedicina una vez que se disponga del equipo y de las credenciales registradas en la cuenta EMOTIV de la universidad.

