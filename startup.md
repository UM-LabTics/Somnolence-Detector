# Guia de arranque del sistema

Como lanzar el sistema completo: **Docker stack en la Mac** + **Detector en la Raspberry Pi 5**.

---

## Arquitectura

```
┌──────────────────────────────────┐         ┌────────────────────────┐
│         Raspberry Pi 5           │         │          Mac           │
│                                  │  MQTT   │                        │
│  detector/main.py                │────────▶│  Mosquitto :1883       │
│    ├─ MediaPipe FaceMesh         │  QoS 1  │  PostgreSQL :5432      │
│    ├─ MediaPipe Hands            │         │  FastAPI :8000         │
│    ├─ SQLite local               │         │  Next.js :3000         │
│    └─ MQTT publisher             │         │                        │
│                                  │         │  http://localhost:3000 │
│  Webcam USB → /dev/video0        │         │                        │
└──────────────────────────────────┘         └────────────────────────┘
```

---

## Mac — Levantar el stack cloud

### 1. Obtener la IP local de la Mac

La Pi necesita esta IP para conectarse al broker MQTT:

```bash
ipconfig getifaddr en0
```

Anotala (ej: `192.168.50.93`). Si estas en WiFi, puede ser `en1` o `en0` segun tu Mac.

### 2. Configurar variables de entorno (primera vez)

El backend usa una clave JWT para firmar los tokens de login. Esa clave (y el resto de secrets de Docker) viven en un archivo `.env` en la raiz del proyecto que **no se commitea** (esta en `.gitignore`).

Si todavia no existe, copia la plantilla y completa los valores:

```bash
cd ~/UM/ProyectoTIC2/Somnolence-Detector
cp .env.example .env
# Generar una clave aleatoria larga:
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# Pegar el resultado en JWT_SECRET_KEY dentro de .env
```

Variables disponibles:

| Variable | Default | Descripcion |
|---|---|---|
| `JWT_SECRET_KEY` | (requerido) | Clave para firmar tokens JWT |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma |
| `JWT_EXPIRATION_MINUTES` | `60` | Vida util del token |

### 3. Levantar todos los servicios

```bash
docker compose up -d
```

Esto arranca 4 contenedores:

| Servicio | Puerto | Descripcion |
|---|---|---|
| `frontend` | 3000 | Dashboard Next.js |
| `backend` | 8000 | API REST FastAPI |
| `postgres` | 5433→5432 | Base de datos PostgreSQL |
| `mosquitto` | 1883, 9001 | Broker MQTT |

### 4. Verificar que todo arranco

```bash
docker compose ps
```

Todos deberian estar en estado `running`/`healthy`.

Verificar endpoints:
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### 5. Crear el usuario admin (solo la primera vez)

Sin un usuario admin no se puede entrar al dashboard. Correr el seed:

```bash
docker compose exec backend python -m scripts.create_admin
```

Credenciales por defecto (cambiar en produccion):

- Email: `admin@somnolence.com`
- Password: `admin123`

El script es idempotente: si el usuario ya existe no hace nada. Para crear admins adicionales o usuarios normales, usar la pantalla `/admin/users` (ver seccion **Autenticacion** abajo).

### 6. Abrir el dashboard

- [http://localhost:3000](http://localhost:3000) — Dashboard (redirige a /login si no hay token)
- [http://localhost:3000/login](http://localhost:3000/login) — Pantalla de login
- [http://localhost:3000/history](http://localhost:3000/history) — Vista historica
- [http://localhost:3000/devices](http://localhost:3000/devices) — Dispositivos
- [http://localhost:3000/admin/users](http://localhost:3000/admin/users) — Gestion de usuarios (solo admin)
- [http://localhost:8000/docs](http://localhost:8000/docs) — Swagger UI de la API

### 7. Ver logs en vivo (opcional)

```bash
docker compose logs -f backend       # API logs
docker compose logs -f mosquitto     # Broker logs
docker compose logs -f               # Todos juntos
```

---

## Raspberry Pi — Lanzar el detector

### Prerequisitos (primera vez)

Si es un setup nuevo, ver `pi_setup_progress.md` en la memoria del proyecto. Resumen:

- Raspberry Pi OS **64-bit Bookworm** (no Trixie — Trixie trae Python 3.13 que no es compatible con MediaPipe)
- Python 3.12 instalado via pyenv
- Venv creado en `~/Somnolence-Detector/detector/venv` con `python -m venv`
- Dependencias instaladas con `pip install -r requirements.txt`
- Webcam USB conectada (verificar con `ls /dev/video*` — debe existir `/dev/video0`)

### 1. Conectar por SSH o terminal

```bash
ssh tic2@<ip-de-la-pi>
```

O abrir una terminal directamente en la Pi si tiene monitor.

### 2. Actualizar codigo desde git

```bash
cd ~/Somnolence-Detector
git pull
```

Si hay cambios locales que te pide guardar y vos queres descartarlos:
```bash
git checkout -- detector/config.py detector/engine.py   # archivos especificos
# o si es general:
git reset --hard HEAD
git pull
```

### 3. Activar venv

```bash
cd detector
source venv/bin/activate
```

Deberia cambiar el prompt a `(venv)`.

### 4. Configurar la IP del broker MQTT

Usa la IP de la Mac que obtuviste arriba:

```bash
export MQTT_BROKER=192.168.50.93
```

Tip: agregalo a `~/.bashrc` para que sea permanente:
```bash
echo 'export MQTT_BROKER=192.168.50.93' >> ~/.bashrc
```

### 5. Lanzar el detector

```bash
python main.py
```

Deberia abrirse una ventana de OpenCV con:
- La imagen de la webcam (espejada)
- Linea 1: `EAR: X.XXX  MAR: X.XXX  PERCLOS: XX.X%`
- Linea 2: `P:X.X Y:X.X R:X.X` (head pose)
- Linea 3: `Hand-Ear: X.XXX` (distancia mano-oreja) — gris si no hay mano
- Banners de alerta abajo cuando se disparan

En los logs de consola se imprime cada alerta detectada:
```
[ALERT] SOMNOLENCIA severity=MEDIUM value=0.254 threshold=0.25
[ALERT] USO DE CELULAR severity=MEDIUM value=0.087 threshold=0.15
```

### 6. Cerrar el detector

- Presionar **`q`** en la ventana de OpenCV
- O **`Ctrl+C`** en la terminal

El shutdown es graceful: cierra la camara, el SQLite local, y desconecta MQTT.

---

## Verificacion end-to-end

Con el stack corriendo en la Mac y el detector en la Pi:

1. **Generar una alerta** (ej: cerrar los ojos ~15 segundos, bostezar, inclinar la cabeza, poner la mano en la oreja)

2. **Verificar en la Mac:**
   ```bash
   # API — listar ultimas alertas
   curl -s "http://localhost:8000/api/alerts/?limit=5" | python3 -m json.tool

   # API — resumen del dashboard
   curl -s "http://localhost:8000/api/dashboard/summary" | python3 -m json.tool

   # Listener MQTT en vivo (opcional, requiere mosquitto-clients)
   docker compose exec mosquitto mosquitto_sub -t 'somnolence/+/#' -v
   ```

3. **Abrir el dashboard** en `http://localhost:3000`:
   - El device de la Pi aparece en `/devices` como activo
   - Las alertas aparecen en el timeline del dashboard
   - Los graficos se actualizan cada 30s

---

## Detener el sistema

### En la Pi
- Presionar `q` o `Ctrl+C` en el detector

### En la Mac

Detener todos los servicios:
```bash
docker compose stop
```

Detener y eliminar los contenedores (los datos se preservan en volumes):
```bash
docker compose down
```

Detener y eliminar **TODO incluyendo datos**:
```bash
docker compose down -v
```

---

## Autenticacion

El sistema usa **JWT** (Bearer tokens) para todas las APIs `/api/*` excepto `/health` y `/api/auth/login`. La pantalla inicial del frontend es `/login`; sin token valido se redirige automaticamente alli.

### Login via API

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@somnolence.com","password":"admin123"}'
```

Devuelve `access_token` (vida util por defecto: 60 min). Usarlo en cualquier llamada protegida:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/devices/
```

### Crear nuevos usuarios

Desde el frontend, loguearse como admin y entrar a [http://localhost:3000/admin/users](http://localhost:3000/admin/users). El form pide nombre, email, contraseña (min. 6 chars) y rol (`ADMIN` u `OPERATOR`).

Tambien se puede hacer via API (solo admin):

```bash
curl -X POST http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"jose@example.com","password":"secret123","full_name":"Jose","role":"OPERATOR"}'
```

### Roles

- `ADMIN`: acceso total + gestion de usuarios.
- `OPERATOR`: acceso al dashboard / dispositivos / historial. No ve la pantalla `/admin/users`.

### Donde se configura la clave JWT

El backend lee `JWT_SECRET_KEY`, `JWT_ALGORITHM` y `JWT_EXPIRATION_MINUTES` desde variables de entorno. En Docker estas vienen del `.env` de la raiz (ver paso 2 arriba). Si cambias `JWT_SECRET_KEY` y reinicias, todos los tokens emitidos previamente quedan invalidos y los usuarios deben volver a loguearse.

### Migraciones de DB (Alembic)

El proyecto incluye Alembic para versionar el esquema. Comandos utiles dentro del contenedor:

```bash
docker compose exec backend alembic current     # revision actual
docker compose exec backend alembic history     # historial
docker compose exec backend alembic upgrade head
```

> Nota: `Base.metadata.create_all()` sigue corriendo al arrancar el backend e inicializa la DB. Alembic queda disponible para aplicar cambios futuros al esquema.

---

## Troubleshooting

### La Pi no se conecta al broker MQTT

**Sintoma:** `MQTT publisher disconnected` en los logs de la Pi, o las alertas no aparecen en el dashboard.

**Checks:**
1. La Mac y la Pi estan en la misma red WiFi/LAN
2. La IP de la Mac es la correcta: `ipconfig getifaddr en0` en la Mac
3. La variable `MQTT_BROKER` esta seteada en la Pi: `echo $MQTT_BROKER`
4. El firewall de la Mac no esta bloqueando el puerto 1883:
   ```bash
   # En la Mac, desde otra terminal
   sudo lsof -i :1883
   ```
5. Test manual desde la Pi:
   ```bash
   nc -zv 192.168.50.93 1883
   # Deberia decir "Connection succeeded"
   ```

### "No face detected" permanente en la Pi

- Iluminacion insuficiente — prender luz
- Camara muy lejos o muy cerca — ajustar distancia (~40-60cm ideal)
- Camara bloqueada — verificar `ls /dev/video*` y que la webcam USB este conectada

### La Pi tira error de MediaPipe al arrancar

- Verificar que el venv esta activado: `which python` debe apuntar a `.../detector/venv/bin/python`
- Verificar la version de Python: `python --version` — debe ser 3.12.x (NO 3.13)
- Si es 3.13, ver `pi_setup_progress.md` para reinstalar con pyenv

### Docker no arranca el backend

```bash
docker compose logs backend --tail 50
```

Errores comunes:
- PostgreSQL no esta healthy — esperar 10s y reintentar `docker compose up -d`
- Puerto 8000 ocupado — `lsof -i :8000` y matar el proceso

### 401 Unauthorized en las APIs

**Causas comunes:**
- El token expiro (60 min por defecto) → volver a loguear.
- Falta el header `Authorization: Bearer <token>` (en el frontend lo maneja `src/lib/api.ts` automaticamente).
- Se cambio `JWT_SECRET_KEY` en `.env` y se reinicio el backend → todos los tokens viejos quedaron invalidos.

### "No se puede entrar al dashboard, redirige a /login"

- Verificar que el seed del admin se haya corrido: `docker compose exec backend python -m scripts.create_admin`
- Credenciales por defecto: `admin@somnolence.com` / `admin123`
- Si olvidaste la contraseña, podes recrear el admin desde la DB:
  ```bash
  docker compose exec postgres psql -U postgres -d somnolence -c "DELETE FROM users WHERE email='admin@somnolence.com';"
  docker compose exec backend python -m scripts.create_admin
  ```

### El dashboard del frontend no se actualiza

- Hard refresh en el navegador: `Cmd+Shift+R`
- Verificar que `NEXT_PUBLIC_API_URL=http://localhost:8000` en `docker-compose.yml`
- Ver logs: `docker compose logs frontend --tail 50`

---

## Testing sin Pi (solo Mac)

Para probar el stack sin la Pi, podes usar el simulador MQTT:

```bash
# Con el stack corriendo
python3 scripts/mqtt_simulator.py --broker localhost --interval 5 --alert-chance 0.5
```

Genera un device ficticio y publica alertas aleatorias (incluye `PHONE_USE`). Util para demos del dashboard sin la Pi fisica.

---

## Archivos clave

| Archivo | Funcion |
|---|---|
| `docker-compose.yml` | Orquestacion de los 4 servicios cloud |
| `detector/main.py` | Entry point del detector en la Pi |
| `detector/config.py` | Umbrales y configuracion del detector |
| `scripts/mqtt_simulator.py` | Simulador para testing sin Pi |
| `mosquitto/config/mosquitto.conf` | Config del broker MQTT |
| `.env` | Variables de entorno para Docker (JWT, no commitear) |
| `.env.example` | Plantilla de `.env` |
| `backend/scripts/create_admin.py` | Seed del usuario admin inicial |
| `backend/alembic/` | Migraciones de la base de datos |
| `backend/app/core/security.py` | Hashing de contraseñas y JWT |
| `backend/app/routers/auth.py` | Endpoints de login y gestion de usuarios |
| `frontend/src/proxy.ts` | Redirige rutas no autenticadas a `/login` |
| `frontend/src/lib/auth-context.tsx` | Contexto React con usuario / login / logout |
