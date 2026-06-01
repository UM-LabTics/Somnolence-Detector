# Parte 5 — Desplegar el detector en la Raspberry Pi (MQTT/TLS a IoT Core)

Esta guía adapta la Pi para que **publique a AWS IoT Core con TLS (8883)** en vez de
a un Mosquitto local (1883). El código ya soporta ambos modos: TLS se activa solo
cuando definís las variables `MQTT_TLS_*`. Sin ellas, sigue funcionando local.

> ✅ **Backend:** el soporte TLS del backend ya está en `develop` (PR de ECS, commit
> `23e904f`). Usa las mismas variables de entorno que la Pi
> (`MQTT_CA_CERT`, `MQTT_CLIENT_CERT`, `MQTT_CLIENT_KEY`), así que la verificación
> end-to-end (paso 5) ya tiene la pieza del backend lista.

---

## 1. Copiar los certificados a la Pi

Los 3 archivos que tenés en tu Mac (en `certs/pi/` o donde los hayas descargado):
Amazon Root CA1, el *device certificate* y la *private key*.

Desde tu **Mac** (reemplazá `<IP_PI>` y los nombres reales de los archivos):

```bash
# En la Pi, crear el destino
ssh pi@<IP_PI> 'mkdir -p ~/somnolence/certs && chmod 700 ~/somnolence/certs'

# Copiar los 3 certificados
scp certs/pi/AmazonRootCA1.pem \
    certs/pi/*-certificate.pem.crt \
    certs/pi/*-private.pem.key \
    pi@<IP_PI>:~/somnolence/certs/

# Bloquear permisos de la clave privada
ssh pi@<IP_PI> 'chmod 600 ~/somnolence/certs/*-private.pem.key'
```

> 🔒 Estos archivos son credenciales. **Nunca** van al repo — ya están en `.gitignore`
> (`certs/`, `*.pem`, `*.key`, `*.crt`).

---

## 2. Traer el código del detector a la Pi

```bash
ssh pi@<IP_PI>
git clone <URL_DEL_REPO> ~/somnolence          # o git pull si ya está clonado
cd ~/somnolence/detector
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## 3. Configurar las variables de entorno

```bash
sudo cp ~/somnolence/detector/deploy/somnolence.env.example /etc/somnolence.env
sudo nano /etc/somnolence.env
```

Verificá que apunten a IoT Core y a los certificados copiados:

| Variable        | Valor                                                      |
|-----------------|------------------------------------------------------------|
| `MQTT_BROKER`   | `a3658r5b4lb2u7-ats.iot.us-east-2.amazonaws.com`           |
| `MQTT_PORT`     | `8883`                                                      |
| `MQTT_CLIENT_ID`| `somnolence-pi-team06` (debe coincidir con el Thing)       |
| `MQTT_CA_CERT`    | ruta absoluta al `AmazonRootCA1.pem`                     |
| `MQTT_CLIENT_CERT`| ruta absoluta al `*-certificate.pem.crt`                |
| `MQTT_CLIENT_KEY` | ruta absoluta al `*-private.pem.key`                    |
| `HEADLESS`      | `true` (sin ventana de OpenCV bajo systemd)                |

---

## 4. Arranque automático con systemd

```bash
sudo cp ~/somnolence/detector/deploy/somnolence-detector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now somnolence-detector

# Ver que arrancó y publica
journalctl -u somnolence-detector -f
```

Buscá en los logs `MQTT TLS enabled (mutual auth)` y `MQTT publisher connected`.

> Si la entrega es solo "mostrar funcionando en vivo", podés saltear systemd y correr
> a mano:
> ```bash
> cd ~/somnolence/detector
> set -a; source /etc/somnolence.env; set +a
> .venv/bin/python main.py
> ```
> (Con `HEADLESS=false` y un display conectado verás la ventana de OpenCV.)

---

## 5. Verificación end-to-end (el momento de la verdad)

Con la Pi publicando, chequeá las tres capas:

1. **IoT Core → MQTT test client / Monitor:** suscribite a `somnolence/#` y deberías
   ver mensajes entrantes en `somnolence/<device_id>/alerts` y `/status`.
2. **Backend en ECS:** los logs deberían mostrar `MQTT connected` y la recepción de
   alertas (el backend ya tiene TLS en develop).
3. **Frontend:** el dashboard debería mostrar el dispositivo online y las alertas
   apareciendo.

Si las tres pasan, el sistema está completo.

---

## Troubleshooting rápido

| Síntoma | Causa probable |
|---------|----------------|
| `[Errno 101] Network is unreachable` / timeout al conectar | La red bloquea el puerto **8883**. Usá `MQTT_PORT=443` + `MQTT_ALPN=x-amzn-mqtt-ca` (caso de la wifi de la facultad) |
| `MQTT connection failed` y nunca conecta | Política de IoT no permite el `client_id`/topic, o el cert no está adjunto al Thing |
| TLS handshake error | Rutas de `MQTT_CA_CERT`/`MQTT_CLIENT_CERT`/`MQTT_CLIENT_KEY` mal, o permisos de la `.key` |
| Conecta pero se desconecta al toque | Otro cliente usando el **mismo** `client_id` (IoT Core expulsa duplicados) |
| `cannot open display` bajo systemd | Falta `HEADLESS=true` en `/etc/somnolence.env` |
| No abre la cámara | `cv2.VideoCapture(0)` sin permisos/cámara; revisá `/dev/video0` |
