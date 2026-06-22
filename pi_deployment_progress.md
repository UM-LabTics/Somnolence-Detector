# Progreso — Despliegue de la Pi a AWS IoT Core (Parte 5)

> Última actualización: 2026-06-08. Si retomás esto en otra sesión, este doc tiene
> todo lo necesario para no volver a perder tiempo en lo ya resuelto.

## 🚦 TL;DR — cómo seguir en otra sesión

**Lo que falta es UNA sola cosa: arreglar la cámara.** Todo lo demás (certs, TLS,
IoT Core, backend ECS, dashboard) está confirmado funcionando. Pasos para
retomar:

1. Reconectate a la Pi: `ssh tic2@172.20.10.11` (IP en la red del celular del
   usuario — puede cambiar, correr `hostname -I` en la Pi si no entra)
2. Activá el venv y corré `v4l2-ctl --list-devices` para encontrar qué
   `/dev/videoN` es la webcam USB real (ver sección "Problema actual" abajo) —
   **quedamos esperando este resultado, es el próximo paso inmediato**
3. Ajustar `detector/config.py` o la variable de entorno correspondiente para
   que apunte al índice correcto de cámara
4. Relanzar `python main.py` y confirmar que la ventana/log no se cierre por
   error de cámara
5. Generar una alerta de prueba (cerrar ojos ~15s, etc.) y verificar que
   aparezca en IoT Core → backend ECS logs → dashboard (sección "Verificación
   end-to-end" abajo, con los comandos AWS CLI ya armados)

**Confirmado en esta sesión:**
- ✅ Pi conecta a AWS IoT Core por MQTT/TLS (dos veces — en red de facultad y en
  hotspot del celular). Logs: `MQTT TLS enabled` → `MQTT publisher connected`
- ✅ Dashboard/API en ECS funcionan (`http://18.116.32.231:3000` confirmado
  desde datos móviles)
- ✅ Identificada la causa de que el dashboard no abriera desde la facultad: esa
  red **solo permite tráfico saliente por el puerto 443** (firewall/proxy de
  campus) — no es un bug de AWS. Por eso también tuvimos que usar
  `MQTT_PORT=443 + ALPN` para la Pi (8883 está bloqueado ahí)
- ❌ **Pendiente**: la cámara USB (`Generalplus GENERAL WEBCAM`, visible en
  `lsusb`) no abre en `/dev/video0` → el detector arranca, conecta MQTT, pero
  se cierra solo al no poder abrir la cámara

## Objetivo

Que la Raspberry Pi publique alertas a **AWS IoT Core** por MQTT/TLS (en vez de a un
Mosquitto local), para que el sistema funcione "desde cualquier red" — no solo
cuando la Pi y el backend están en la misma LAN. El backend en ECS ya está
suscrito a IoT Core (ver rama `develop`, PR de ECS).

## Estado: la Pi YA está publicando a IoT Core con éxito ✅

Lo más difícil está resuelto. Esto es lo que falta confirmar end-to-end (ver
sección "Qué falta" abajo).

---

## Datos clave (anotar / no perder)

### Acceso a la Raspberry Pi
- **Hostname**: `TIC2`
- **Usuario**: `tic2`
- **IP actual**: `10.252.50.26` (red de la facultad — **cambia** cada vez que se
  reconecta; para obtenerla de nuevo, conectar monitor/teclado a la Pi y correr
  `hostname -I`. OJO: en Linux es `hostname -I`, NO `ipconfig` — eso es de Mac/Windows)
- **SSH**: `ssh tic2@10.252.50.26`
- Repo clonado en `~/Somnolence-Detector`, rama `develop` (commit `5f1fa66`,
  ya tiene el merge de `feat/pi-mqtt-tls` y `feat/pi-mqtt-alpn`)
- Venv en `~/Somnolence-Detector/detector/venv` (Python 3.12.13 — confirmado OK)

### Certificados de AWS IoT Core (mutual TLS)
Ubicados en el repo, en `certs/pi/` (en la Mac, raíz del proyecto):
- `AmazonRootCA1.pem`
- `2bea401029b61dd0f50cb52c2df32daf2bc557513828c81b7efdeae379dfbebd-certificate.pem.crt`
- `2bea401029b61dd0f50cb52c2df32daf2bc557513828c81b7efdeae379dfbebd-private.pem.key`

Ya copiados a la Pi en `~/somnolence/certs/` (permisos `600` en la private key).
**`certs/` ya está en `.gitignore`** (lo agregué yo — antes NO estaba, a pesar de
que el README decía que sí. Revisar que nunca se suba con `git status`).

### Config de la Pi: `/etc/somnolence.env`
Ya creado y funcionando. Contenido completo:
```
MQTT_BROKER=a3658r5b4lb2u7-ats.iot.us-east-2.amazonaws.com
MQTT_TOPIC_PREFIX=somnolence
MQTT_PORT=443
MQTT_ALPN=x-amzn-mqtt-ca
MQTT_CLIENT_ID=somnolence-pi-team06
MQTT_CA_CERT=/home/tic2/somnolence/certs/AmazonRootCA1.pem
MQTT_CLIENT_CERT=/home/tic2/somnolence/certs/2bea401029b61dd0f50cb52c2df32daf2bc557513828c81b7efdeae379dfbebd-certificate.pem.crt
MQTT_CLIENT_KEY=/home/tic2/somnolence/certs/2bea401029b61dd0f50cb52c2df32daf2bc557513828c81b7efdeae379dfbebd-private.pem.key
HEADLESS=true
MOCK_SENSORS=true
MOCK_ACTUATORS=true
```
> **Por qué 443 + ALPN en vez de 8883**: la red de la facultad (`10.252.x.x`)
> bloquea el puerto 8883. AWS IoT Core acepta MQTT+mTLS sobre 443 usando ALPN
> (`x-amzn-mqtt-ca`). El código en `detector/mqtt_publisher.py` ya soporta
> ambos modos automáticamente según si `MQTT_ALPN` está seteado.

> **MOCK_SENSORS / MOCK_ACTUATORS = true**: la Pi todavía no tiene el hardware
> real (buzzer, DHT11) conectado — son mocks por ahora. Cuando se conecte el
> hardware real (rama `feat/pi-hardware-integration` ya tiene el código),
> cambiar a `false`.

### Prueba manual exitosa (correr el detector a mano)
```bash
cd ~/Somnolence-Detector/detector
source venv/bin/activate
set -a; source /etc/somnolence.env; set +a
python main.py
```
Logs que confirman que anduvo:
```
[mqtt_publisher] INFO: MQTT TLS enabled (mutual auth, ALPN=x-amzn-mqtt-ca)
[mqtt_publisher] INFO: MQTT connecting to a3658r5b4lb2u7-ats.iot.us-east-2.amazonaws.com:443
[mqtt_publisher] INFO: MQTT publisher connected
```
Device ID generado: `d0f9d7cc-1456-43e6-a23b-dd8b2434c287`

### AWS — acceso por CLI (SSO)
Perfil ya configurado en la Mac (`~/.aws/config`):
```bash
export AWS_PROFILE=Estudiante-374648537332
aws sso login --profile Estudiante-374648537332   # re-loguear cuando expire
aws sts get-caller-identity
```
- SSO start URL: `https://d-9067fcfddf.awsapps.com/start/`
- Cuenta AWS: `374648537332`, rol `Estudiante`, región `us-east-2`

### AWS — estado del cluster ECS (verificado hoy)
- Cluster: `somnolence-cluster`
- Servicios: `somnolence-backend-svc` y `somnolence-frontend-svc`, ambos
  `ACTIVE`, `desired=1 running=1` — **están arriba**, no hace falta escalarlos
- **IPs públicas actuales** (cambiaron desde la última sesión, la vieja
  `3.138.123.214` ya no sirve — Fargate asigna IP nueva en cada restart):
  - Backend: `16.58.227.81` (puerto 8000)
  - Frontend: `18.116.32.231` (puerto 3000)
- Cómo volver a obtenerlas si cambian de nuevo:
  ```bash
  export AWS_PROFILE=Estudiante-374648537332
  aws ecs list-tasks --cluster somnolence-cluster --region us-east-2 --query 'taskArns' --output text
  # por cada task ARN, sacar el eni-... con:
  aws ecs describe-tasks --cluster somnolence-cluster --region us-east-2 --tasks <TASK_ID> \
    --query 'tasks[0].{group:group,eni:attachments[0].details}'
  # y la IP pública del ENI con:
  aws ec2 describe-network-interfaces --region us-east-2 --network-interface-ids <eni-...> \
    --query 'NetworkInterfaces[].{eni:NetworkInterfaceId,publicIp:Association.PublicIp}'
  ```

---

## Qué falta (próximos pasos, en orden)

1. **🟡 DIAGNOSTICADO — no es un problema de AWS, es la red de la facultad**:
   las IPs `16.58.227.81:8000` (backend) y `18.116.32.231:3000` (frontend) dan
   timeout desde la red `10.252.x.x`. Verificación completa del lado AWS — TODO
   bien configurado:
   - Security group `somnolence-tasks-sg` permite `0.0.0.0/0` en 3000 y 8000 ✅
   - NACL del subnet permite todo el tráfico ✅
   - Route table tiene `0.0.0.0/0 -> igw-03d62ac486d4e4c13` (IGW `available`) ✅
   - ENI tiene IP pública asociada correctamente, container `RUNNING`,
     servicio en "steady state" ✅

   **La prueba que lo confirma**: a la *misma IP* `16.58.227.81`...
   - puerto **443** → conecta (`nc -zv` succeeded)
   - puerto **8000** (la API) → timeout
   - puerto **22** (SSH) → timeout

   Conclusión: la red de la facultad **solo deja pasar tráfico saliente por el
   puerto 443** (probablemente proxy/firewall transparente — el mismo motivo
   por el que la Pi tuvo que usar `MQTT_PORT=443 + ALPN` en vez de 8883).
   El dashboard/API en 3000/8000 **no son alcanzables desde la facultad por IP
   directa**, sin importar cuál sea la IP del momento.

   **Soluciones**:
   - Corto plazo: acceder al dashboard desde otra red (datos móviles, wifi de
     casa) — eso confirma que el sistema funciona, solo que no desde la facultad
   - Largo plazo / recomendado: poner un **Application Load Balancer (ALB) con
     HTTPS en 443** delante de los servicios ECS. Esto resuelve DOS problemas a
     la vez: (a) acceso desde redes restrictivas como la de la facultad, y
     (b) la URL/IP deja de cambiar en cada restart de Fargate (responde la
     pregunta de "¿asignamos Elastic IP?" — con Fargate awsvpc no es la solución
     natural porque cada restart genera un ENI nuevo; el ALB sí da un endpoint
     estable vía DNS)

2. **Verificación end-to-end** (una vez que el backend responda):
   - IoT Core → MQTT test client: suscribirse a `somnolence/#`, deberían aparecer
     mensajes de `somnolence/d0f9d7cc.../alerts` y `/status`
   - Backend ECS logs: deberían mostrar `MQTT connected` y alertas recibidas
   - Dashboard (frontend): el device debería aparecer online en `/devices` y las
     alertas en el timeline

3. **Considerar Elastic IP / Load Balancer** (lo planteó Phillip): Fargate genera
   un ENI nuevo en cada restart de task, así que una Elastic IP habría que
   re-asociarla manualmente cada vez — no es la solución natural. Lo estándar
   para tener un endpoint estable con ECS Fargate es poner un **Application
   Load Balancer** delante del servicio (DNS fijo, no cambia con los restarts).
   Pendiente de decidir si vale la pena para este proyecto académico o si
   alcanza con re-consultar la IP cada vez (como hicimos hoy).

4. **Setup de systemd** (opcional, recomendado para la demo):
   - Archivos ya están en `detector/deploy/`:
     `somnolence-detector.service`, `somnolence.env.example`, `README-pi.md`
   - Pasos: copiar el `.service` a `/etc/systemd/system/`,
     `daemon-reload`, `enable --now`, revisar con `journalctl -u somnolence-detector -f`
   - Si la entrega es solo "mostrar funcionando en vivo", se puede saltear y
     correr `python main.py` a mano

5. **Limpieza post-entrega** (cuando el proyecto termine, según indicó el amigo):
   bajar `desired-count` a 0 en ambos servicios ECS, apagar/eliminar RDS, borrar
   repos ECR.

---

## 🔴 Problema actual — la cámara no abre (PRÓXIMO PASO)

Al correr `python main.py` en la Pi (con MQTT ya conectando bien), el programa
se cierra solo apenas arranca:
```
[ WARN] global cap_v4l.cpp:913 open VIDEOIO(V4L2:/dev/video0): can't open camera by index
[ERROR] global obsensor_uvc_stream_channel.cpp:158 getStreamChannelGroup Camera index out of range
[__main__] INFO: Shutting down...
```
Pero la webcam SÍ está conectada:
```
$ lsusb | grep -i cam
Bus 001 Device 003: ID 1b3f:2247 Generalplus Technology Inc. GENERAL WEBCAM

$ ls /dev/video*
/dev/video0  /dev/video1  /dev/video19 ... /dev/video35   (36 dispositivos!)
```

**Causa probable**: la Raspberry Pi 5 expone un montón de `/dev/videoN`
(pipeline de cámara CSI/ISP vía libcamera, codecs HW, etc.) además del índice
real de la webcam USB. `cv2.VideoCapture(0)` está abriendo el índice equivocado.

**Próximo paso exacto** (quedamos acá, sin ejecutar):
```bash
ssh tic2@172.20.10.11   # o la IP que tenga en ese momento (hostname -I)
cd ~/Somnolence-Detector/detector && source venv/bin/activate
v4l2-ctl --list-devices   # si no está instalado: sudo apt-get install -y v4l-utils
```
Esto agrupa los `/dev/videoN` por dispositivo físico y muestra cuál bloque
corresponde al "GENERAL WEBCAM" (USB). Una vez identificado el índice correcto:
- Revisar cómo `detector/main.py` / `detector/sensors.py` abre la cámara
  (probablemente `cv2.VideoCapture(<algo>)`) y si hay una env var tipo
  `CAMERA_INDEX` o `VIDEO_DEVICE` en `detector/config.py` para configurarlo
  sin tocar código — si no existe, puede que haya que agregarla o hardcodear
  el índice correcto temporalmente para la demo
- Probar de nuevo `python main.py` y confirmar que la ventana de OpenCV (o,
  en `HEADLESS=true`, los logs de FPS/EAR/MAR) aparezcan sin el error de cámara

## Verificación end-to-end (una vez que la cámara abra)

Con el detector corriendo y generando alertas (cerrar ojos ~15s, bostezar,
etc.), verificar las 3 capas — comandos AWS CLI ya probados y listos:

```bash
export AWS_PROFILE=Estudiante-374648537332
# (re-loguear si expiró: aws sso login --profile Estudiante-374648537332)

# 1. Backend logs en ECS — buscar mensajes MQTT recibidos del device
aws logs tail /ecs/somnolence-backend --region us-east-2 --since 10m --follow
# (el log group puede tener otro nombre — listar con: aws logs describe-log-groups --region us-east-2)

# 2. Confirmar IPs públicas actuales del backend/frontend (cambian en cada restart)
aws ecs list-tasks --cluster somnolence-cluster --region us-east-2 --query 'taskArns' --output text
# luego describe-tasks -> eni-... -> describe-network-interfaces -> publicIp (ver comandos completos arriba)

# 3. Dashboard — abrir desde una red que NO sea la facultad (datos móviles):
#    http://<IP-frontend-actual>:3000  ->  /devices (debería verse el device
#    d0f9d7cc-1456-43e6-a23b-dd8b2434c287 online) y el timeline de alertas
```

## Notas / troubleshooting que ya resolvimos

- `ssh tic2@10.252.48.255` fallaba con "connection refused" porque esa IP era
  **la de la Mac** (`ipconfig getifaddr en0`), no la de la Pi — error de tipeo
  de contexto, no de configuración.
- `ipconfig` no existe en Linux — en la Pi usar `hostname -I`.
- Los certs estaban en `certs/pi/` en la raíz del repo (Mac) — no había que
  regenerarlos en IoT Core.
- El código de soporte TLS/ALPN para la Pi YA estaba mergeado en `develop`
  (PRs #7 `feat/pi-mqtt-tls` y #8 `feat/pi-mqtt-alpn`) — no hubo que escribir
  código nuevo, solo desplegar/configurar.
