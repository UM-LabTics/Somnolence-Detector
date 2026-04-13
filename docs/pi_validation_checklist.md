# Pi 5 — Validation Checklist

Checklist end-to-end para dejar la Pi 5 corriendo el detector completo (Hand-Ear + YOLO PHONE_OBJECT) contra el stack de la Mac. Ejecutar en orden; cada paso tiene un resultado esperado y un bloque de troubleshooting.

Asume que el stack cloud de la Mac ya arranca con `docker compose up -d` (ver `startup.md` sección "Mac — Levantar el stack cloud").

---

## 0 — Prerequisitos físicos

- Pi 5 con Debian Bookworm o Trixie, acceso SSH o monitor
- Webcam USB conectada
- Pi en la misma LAN que la Mac
- Modelo YOLO exportado previamente en tu laptop (ver `detector/models/README.md`) y commiteado o subido por scp

---

## 1 — Setup del runtime Python

```bash
ssh tic2@<ip-de-la-pi>
cd ~/Somnolence-Detector
git pull
YOLO=1 bash scripts/setup_pi.sh
```

**Esperado:** `Done. Next steps:` al final y las líneas de smoke-test imprimen versiones de `mediapipe`, `opencv`, `numpy` y `ncnn: installed`. `/dev/video0 present`.

**Si falla pyenv install:** la compilación de Python 3.12 tarda 15-30 min en la Pi 5. Si sigue fallando, chequear que las libs de build estén (`libssl-dev libffi-dev libsqlite3-dev`). Si el reloj está desincronizado (`"certificate not yet valid"`), correr `sudo timedatectl set-ntp true`.

**Si falla ncnn install:** el detector funciona igual sin ncnn — sólo no dispara `PHONE_OBJECT`. Para este checklist, resolverlo antes de seguir: normalmente `pip install ncnn` trae un wheel aarch64. Si no, compilar ncnn desde source con CMake.

---

## 2 — Copiar el modelo YOLO

Si no lo commiteaste, desde tu laptop:

```bash
scp detector/models/yolo11n_416.ncnn.{param,bin} tic2@<ip-pi>:~/Somnolence-Detector/detector/models/
```

**Esperado:**

```bash
ssh tic2@<ip-pi> 'ls -la ~/Somnolence-Detector/detector/models/'
# yolo11n_416.ncnn.param   (~50 KB)
# yolo11n_416.ncnn.bin     (~3 MB)
```

---

## 3 — Configurar MQTT broker + YOLO

```bash
ssh tic2@<ip-pi>
cd ~/Somnolence-Detector/detector
source venv/bin/activate
export MQTT_BROKER="<ip-de-la-mac>"       # ej. 192.168.50.93
export YOLO_ENABLED=true
```

**Esperado:** `echo $MQTT_BROKER` imprime la IP; `echo $YOLO_ENABLED` imprime `true`.

---

## 4 — Benchmark de latencia YOLO

```bash
python ../scripts/benchmark_yolo.py
```

**Esperado:** `p95 < 200 ms`. Línea final: `Pi 5 target p95 < 200 ms → OK`.

**Si `SLOW`:** bajar `yolo_input_size` a 320 en `detector/config.py` (o agregar un export YOLO_INPUT_SIZE si decidís parametrizarlo por env). Recorrer: p95 debería caer a ~100 ms.

---

## 5 — Lanzar el detector

Con monitor conectado:
```bash
python main.py
```

Sin monitor (Pi headless):
```bash
python main.py --no-display
```

**Esperado en los logs:**
- `Device ID: <uuid>`
- `YOLO phone-object detection: enabled`
- `Somnolence Detector started in (display|headless) mode`
- Cada 5s: `[PIPELINE] fps=XX.X yolo_bbox=(yes|no)`. Target FPS efectivo: >20.

Si hay monitor: ventana OpenCV con líneas EAR/MAR/PERCLOS, head pose, Hand-Ear, y cuando acercás un celular a la cámara aparece un **rectángulo magenta con `PHONE 0.XX`**.

**Si `[PIPELINE] fps` es muy bajo (<10):** YOLO está sobrecargando CPU. Bajar `yolo_input_size` o subir `yolo_frame_interval` implícito (ya está en drop-oldest, así que el único knob es el input_size). Si persiste, revisar `top`/`htop` para ver si mediapipe está pegándole también.

---

## 6 — Verificar eventos en el dashboard

En la Mac:

```bash
# Sucriber a los topics MQTT
docker compose exec mosquitto mosquitto_sub -t 'somnolence/#' -v
```

Simultáneamente, delante de la cámara de la Pi:

**Test A — PHONE_USE (Hand-Ear):** sostener el celular contra la oreja durante 3+ segundos.
**Esperado:** evento `PHONE_USE` MEDIUM y luego HIGH en MQTT y en el timeline de `http://localhost:3000`.

**Test B — PHONE_OBJECT (YOLO):** sostener el celular en la mano frente al volante/torso, sin llevarlo a la oreja, mirando al teléfono.
**Esperado:** a los ~2.5s evento `PHONE_OBJECT` MEDIUM con `metadata.trigger` en `{iou_hand, near_ear, head_nod}`. A los ~10s escala a HIGH. Ver el chip "Celular detectado" en el breakdown del dashboard, color rojo-naranja (chart-4) distinto del violeta de "Uso de celular".

**Test C — ambos simultáneos:** celular pegado a la oreja. Deben disparar AMBOS alert_types (evidencia redundante).

---

## 7 — Persistencia offline

Desconectar la WiFi de la Pi (mantener la cámara conectada):

1. Generar una alerta (bostezo, cerrar ojos).
2. En los logs: `MQTT publisher disconnected` + `queued alert locally` (SQLite).
3. Reconectar WiFi.
4. **Esperado:** `synced N buffered alerts` en los logs y las alertas aparecen en el dashboard con el timestamp real (no el de reconexión).

---

## 8 — Shutdown limpio

- Con monitor: presionar `q` en la ventana OpenCV.
- Headless: `Ctrl+C` en la SSH, o `kill -TERM <pid>` desde otra sesión.

**Esperado:** `Shutting down...` → `Shutdown complete`. No debe quedar el proceso colgado (revisar con `pgrep -f main.py`).

---

## Métricas de éxito para la defensa TIC II

- FPS efectivo del pipeline ≥ 20 con YOLO habilitado
- p95 latencia YOLO < 200 ms a 416×416
- Ambos canales (`PHONE_USE` y `PHONE_OBJECT`) disparando con sus thresholds de tiempo
- Buffer offline SQLite con replay al reconectar
- Dashboard mostrando los 5 tipos con color y código distintos
