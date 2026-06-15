# DEPLOY.md — Runbook de despliegue y solución durable

> Plan documentado de la infraestructura de despliegue (ECS Fargate) y de las
> mejoras pendientes para eliminar el problema de las IPs cambiantes y
> automatizar los deploys. Escrito 2026-06-08. Acompaña a
> [`pi_deployment_progress.md`](pi_deployment_progress.md) (lado Raspberry Pi).

---

## 0. Estado actual (lo que está vivo hoy)

Sistema en **AWS account `374648537332`, región `us-east-2`**, perfil SSO
`Estudiante-374648537332`.

| Componente | Dónde | Estado |
|---|---|---|
| Detector (Pi) | Raspberry Pi `tic2@<ip>` | ✅ Publica a IoT Core por MQTT/TLS 443+ALPN |
| AWS IoT Core | broker `a3658r5b4lb2u7-ats.iot.us-east-2.amazonaws.com` | ✅ Recibe `somnolence/#` |
| Backend | ECS `somnolence-backend-svc` (FastAPI, :8000) | ✅ Ingesta MQTT → RDS, sirve `/api/*` |
| Frontend | ECS `somnolence-frontend-svc` (Next.js, :3000) | ✅ Sirve dashboard |
| Cluster | `somnolence-cluster` | ✅ `desired=1 running=1` ambos |

**Red del cluster (awsvpc):**
- VPC `vpc-061ca11ae1f546d7d`
- Subnets públicas: `subnet-09913be5d49855389`, `subnet-05ee40cdb5dc84b8c`
- Security group de tasks: `sg-01bf74a4cba528f29` (permite 3000 y 8000 desde `0.0.0.0/0`)
- `assignPublicIp: ENABLED`
- Exec role: `ecsTaskExecutionRole`

### ✅ RESUELTO (2026-06-15) — Fase 1 (ALB) y Fase 2 (imagen prod del front)
El parche temporal de la IP horneada **ya no aplica**: se desplegó el ALB y la
imagen de producción del frontend. El endpoint estable es:

> **`https://somnolence-alb-1116710331.us-east-2.elb.amazonaws.com`** (DNS fijo,
> no cambia nunca más; cert self-signed → el browser pide "continuar").

El frontend ahora llama `/api/*` **same-origin** (al mismo ALB) — no hay ninguna
IP/DNS de backend horneado. Ver "Recursos reales" abajo y el detalle en cada fase.

### Recursos reales desplegados (us-east-2, account 374648537332)
| Recurso | ID / ARN |
|---|---|
| ALB | `somnolence-alb` — `arn:...:loadbalancer/app/somnolence-alb/a12aec02a362cf0d` |
| DNS del ALB | `somnolence-alb-1116710331.us-east-2.elb.amazonaws.com` |
| Listener 443 | `arn:...:listener/app/somnolence-alb/a12aec02a362cf0d/cc44883f834fcbbb` |
| TG backend | `somnolence-tg-backend` (`/health`) — `arn:...:targetgroup/somnolence-tg-backend/10feb5f8b258f9b0` |
| TG frontend | `somnolence-tg-frontend` (`/`) — `arn:...:targetgroup/somnolence-tg-frontend/63010d75a32c33a9` |
| SG del ALB | `somnolence-alb-sg` — `sg-026d44eda220a5d9f` (80/443 a internet) |
| Cert ACM | `arn:...:certificate/b6e14e6e-df4a-45ef-b2c9-2e5368379aea` (self-signed, CN `somnolence-demo.local`) |
| Task-def frontend prod | `somnolence-frontend:4` (imagen `somnolence-frontend:prod-3be8db0`) |

### Los dos problemas de raíz que este plan resuelve
1. **IPs cambiantes**: Fargate/awsvpc asigna un **ENI nuevo por task** en cada
   restart → la IP pública cambia. Elastic IP no se asocia de forma persistente
   a tasks Fargate. **Solución estándar: ALB con DNS fijo.**
2. **Acoplamiento frontend↔IP del backend**: el frontend (Next.js) llama al
   backend por IP. Con el ALB + routing por path, el frontend llama
   **same-origin `/api`** y la IP **deja de existir** como config.

---

## Arquitectura objetivo

```
                         Internet
                            │
                            ▼
                 ┌─────────────────────┐
                 │   ALB (DNS fijo)    │  listener :443 (TLS)
                 │  somnolence-alb     │  + :80 → redirect 443
                 └─────────┬───────────┘
              path /api/*  │  path /  (default)
              /docs /health│
                  ▼        ▼
          ┌──────────┐  ┌───────────┐
          │ backend  │  │ frontend  │   target groups (IP target type)
          │  :8000   │  │  :3000    │
          └────┬─────┘  └───────────┘
               ▼
          RDS + IoT Core
```

El frontend se sirve en `/`, y sus llamadas a la API van a `/api/*` del **mismo
origen** (el ALB), que el listener rutea al target group del backend. Resultado:
`NEXT_PUBLIC_API_URL` pasa a ser `""` (same-origin) o el DNS del ALB — y **nunca
más cambia**.

---

## Fase 1 — ALB (la pieza que mata el problema de las IPs) ✅ HECHA (2026-06-15)

> Decisión tomada: **sin dominio → cert self-signed importado a ACM**. Pasa el
> firewall de la facultad (sigue siendo TLS/443); el browser muestra "no seguro
> / continuar" — aceptable para demo académica. Si más adelante hay dominio,
> reemplazar por cert ACM validado por DNS (HTTPS limpio).

> **⚠️ Gotcha encontrado en 1.1:** ACM/ELB **rechaza** el cert si el CN no es un
> FQDN. `-subj "/CN=somnolence-demo"` falla con `UnsupportedCertificate` al crear
> el listener. Usar un CN con punto + SAN:
> `-subj "/CN=somnolence-demo.local" -addext "subjectAltName=DNS:somnolence-demo.local"`.

> **Nota 1.5:** `update-service --load-balancers` funcionó sin recrear los
> servicios (ambos no tenían LB previo).

### 1.1 Cert self-signed → ACM
```bash
export AWS_PROFILE=Estudiante-374648537332
# generar cert self-signed (CN cualquiera, no hay dominio)
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout /tmp/alb-key.pem -out /tmp/alb-cert.pem \
  -subj "/CN=somnolence-demo"
CERT_ARN=$(aws acm import-certificate --region us-east-2 \
  --certificate fileb:///tmp/alb-cert.pem \
  --private-key fileb:///tmp/alb-key.pem \
  --query CertificateArn --output text)
echo "$CERT_ARN"
```

### 1.2 Security group del ALB (abre 80/443 a internet)
```bash
ALB_SG=$(aws ec2 create-security-group --region us-east-2 \
  --group-name somnolence-alb-sg --description "ALB somnolence" \
  --vpc-id vpc-061ca11ae1f546d7d --query GroupId --output text)
aws ec2 authorize-security-group-ingress --region us-east-2 --group-id "$ALB_SG" \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --region us-east-2 --group-id "$ALB_SG" \
  --protocol tcp --port 80 --cidr 0.0.0.0/0
# permitir que el ALB hable con las tasks en 8000 y 3000
aws ec2 authorize-security-group-ingress --region us-east-2 \
  --group-id sg-01bf74a4cba528f29 --protocol tcp --port 8000 --source-group "$ALB_SG"
aws ec2 authorize-security-group-ingress --region us-east-2 \
  --group-id sg-01bf74a4cba528f29 --protocol tcp --port 3000 --source-group "$ALB_SG"
```

### 1.3 ALB + target groups (target type `ip`, requerido por Fargate)
```bash
ALB_ARN=$(aws elbv2 create-load-balancer --region us-east-2 \
  --name somnolence-alb --type application --scheme internet-facing \
  --subnets subnet-09913be5d49855389 subnet-05ee40cdb5dc84b8c \
  --security-groups "$ALB_SG" \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

TG_BACK=$(aws elbv2 create-target-group --region us-east-2 \
  --name somnolence-tg-backend --protocol HTTP --port 8000 \
  --vpc-id vpc-061ca11ae1f546d7d --target-type ip \
  --health-check-path /health \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

TG_FRONT=$(aws elbv2 create-target-group --region us-east-2 \
  --name somnolence-tg-frontend --protocol HTTP --port 3000 \
  --vpc-id vpc-061ca11ae1f546d7d --target-type ip \
  --health-check-path / \
  --query 'TargetGroups[0].TargetGroupArn' --output text)
```

### 1.4 Listeners (443 con routing por path; 80 redirige a 443)
```bash
# 443: default → frontend
LISTENER=$(aws elbv2 create-listener --region us-east-2 \
  --load-balancer-arn "$ALB_ARN" --protocol HTTPS --port 443 \
  --certificates CertificateArn="$CERT_ARN" \
  --default-actions Type=forward,TargetGroupArn="$TG_FRONT" \
  --query 'Listeners[0].ListenerArn' --output text)

# regla: /api/*, /docs, /health, /openapi.json → backend
aws elbv2 create-rule --region us-east-2 --listener-arn "$LISTENER" --priority 10 \
  --conditions Field=path-pattern,Values='/api/*','/docs','/health','/openapi.json' \
  --actions Type=forward,TargetGroupArn="$TG_BACK"

# 80 → redirect a 443
aws elbv2 create-listener --region us-east-2 \
  --load-balancer-arn "$ALB_ARN" --protocol HTTP --port 80 \
  --default-actions 'Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'
```

### 1.5 Enganchar los servicios ECS a los target groups
> `update-service` con `--load-balancers` requiere que el servicio lo soporte;
> si tira error, recrear el servicio con la config de LB. Cada servicio
> registra su IP de task automáticamente en el TG.
```bash
aws ecs update-service --cluster somnolence-cluster --region us-east-2 \
  --service somnolence-backend-svc \
  --load-balancers targetGroupArn="$TG_BACK",containerName=backend,containerPort=8000
aws ecs update-service --cluster somnolence-cluster --region us-east-2 \
  --service somnolence-frontend-svc \
  --load-balancers targetGroupArn="$TG_FRONT",containerName=frontend,containerPort=3000
```

### 1.6 Apuntar el frontend al ALB y verificar
```bash
ALB_DNS=$(aws elbv2 describe-load-balancers --region us-east-2 \
  --names somnolence-alb --query 'LoadBalancers[0].DNSName' --output text)
echo "Dashboard: https://$ALB_DNS"
```
- Registrar nueva revisión de `somnolence-frontend` con
  `NEXT_PUBLIC_API_URL=https://$ALB_DNS` (o `""` para same-origin si se ajusta
  `src/lib/api.ts` a path relativo) y redeploy.
- **Verificar (lo que hay que correr SIEMPRE post-deploy, "asegurate que ande"):**
  ```bash
  curl -sk https://$ALB_DNS/health
  curl -sk https://$ALB_DNS/api/devices/ | python3 -m json.tool | head
  curl -sk -o /dev/null -w "front %{http_code}\n" https://$ALB_DNS/
  ```
  Los tres OK ⇒ dashboard funciona y **la URL ya no cambia nunca más**.

✅ **Resultado Fase 1:** endpoint estable (DNS del ALB) + accesible desde la
facultad (443) + frontend desacoplado de la IP del backend.

---

## Fase 2 — Imágenes prod-ready + compose dev separado 🟢 frontend HECHO (2026-06-15)

> **✅ Frontend hecho:** `frontend/Dockerfile` ahora es multi-stage `next build`
> + `output: standalone` + `node server.js` (en vez de `npm run dev`).
> `next.config.ts` con `output: "standalone"`. `src/lib/api.ts` quedó same-origin
> (`?? ""`) → el front llama `/api/*` al ALB, sin IP horneada (build-arg
> `NEXT_PUBLIC_API_URL=""`). En el rollback de la fase 1 el `next dev` daba health
> check con timeout (recompila por request); la imagen prod arranca rápido y el
> health check de `/` pasa. Commit en rama `feat/frontend-prod-build`.
> **Gotcha:** `next build` corre type-check (a diferencia de `next dev`) y
> destapó 2 bugs de tipos reales (history-chart, alerts-history-table) — ya
> arreglados. Correr `npx tsc --noEmit` local antes de buildear amd64 (lento).
> **Pendiente:** revisar/confirmar imagen prod del **backend** y opcional
> `docker-compose.prod.yml`.

**Aclaración clave — "dev" significa dos cosas, no confundirlas:**
- **`next dev` (el _modo_ de desarrollo):** hot-reload, recompila on-demand, lee
  env en runtime, sin optimizar. Tiene sentido **solo donde se edita el código
  fuente en vivo** (laptop, con los volumes del compose montados).
- **un entorno _desplegado_ (aunque le digas "stage dev"):** corre en un server
  (ECS), nadie edita código ahí adentro.

**Regla:** `next dev` **nunca** en algo desplegado. Si está en ECS, va build de
producción — da igual si el entorno se llama "dev" o "prod". Correr `next dev` en
ECS (lo que pasa hoy) es un anti-pattern: arranca lento (recompila en el primer
request → se ve `HTTP 000` y luego `200`), consume más CPU/RAM y sirve payloads
sin optimizar. (Hoy nos *convino* solo porque lee env en runtime y permitió el
quick-fix sin rebuild — efecto secundario, no la forma correcta.)

| | Modo | Dónde |
|---|---|---|
| Local (editando código) | `next dev` (compose con volumes) | Tu máquina |
| Cualquier cosa desplegada | `next build` + `next start` / standalone | ECS |

**Problema concreto:** [`frontend/Dockerfile`](frontend/Dockerfile) hace
`CMD ["npm", "run", "dev"]` y esa imagen se empujó a ECS. Hay que separarlo:

- **`frontend/Dockerfile` (prod, para ECS):** multi-stage con `next build` +
  output `standalone` + `node server.js`. Ajustar `next.config.ts` con
  `output: "standalone"`. Ojo: en build de prod `NEXT_PUBLIC_API_URL` se
  **hornea** → con el ALB ya no importa (same-origin), o pasarlo como build-arg.
- **Compose:** mantener [`docker-compose.yml`](docker-compose.yml) para **dev
  local** (hot-reload, volumes, mosquitto+postgres locales — ahí `next dev` está
  bien). Opcional `docker-compose.prod.yml` que use las imágenes buildeadas.
- Regla en docs: **dev local = compose (`next dev`)**, **desplegado = imagen
  buildeada en ECR vía Fase 3**. Nunca `npm run dev` en ECS.

---

## Fase 3 — GitHub Actions (deploy automático) 🟡

> Repo: `github.com/phillipbowles/Somnolence-Detector`.
> **CI/CD NO arregla las IPs** (eso es la Fase 1). Esto da reproducibilidad:
> push a una rama → build → push ECR → update service, sin pasos manuales.

**Auth recomendada: OIDC** (sin access keys de larga vida):
1. Crear OIDC provider de GitHub en IAM (`token.actions.githubusercontent.com`).
2. Rol `gha-somnolence-deploy` con trust al repo y permisos:
   `ecr:*` (push), `ecs:RegisterTaskDefinition`, `ecs:UpdateService`,
   `ecs:DescribeServices`, `iam:PassRole` (sobre `ecsTaskExecutionRole`).
3. Repos ECR: `somnolence-backend`, `somnolence-frontend` (crear si no existen).

**Workflow `.github/workflows/deploy.yml` (por servicio):**
```
on: push (rama deploy/prod, o tag)
jobs:
  - configure-aws-credentials (role-to-assume: gha-somnolence-deploy)
  - login ECR
  - docker build + push  (tag = git sha)
  - render task-def (aws-actions/amazon-ecs-render-task-definition)
  - deploy (aws-actions/amazon-ecs-deploy-task-definition, wait-for-stability)
```
Usar `backend-task-def.json` como base para el render del backend; crear el
equivalente `frontend-task-def.json`. **Secrets necesarios** (los certs IoT del
backend que escribe `entrypoint.sh`): guardar en GitHub Secrets o, mejor, en
**AWS Secrets Manager** y leerlos desde la task def (`secrets:` en el container).

**Post-deploy del workflow:** smoke test contra el ALB (los 3 `curl` de la
Fase 1.6) y fallar el job si alguno no da 200.

---

## Fase 4 — Documentación / consistencia 🟢 (transversal)

- Este `DEPLOY.md` = fuente de verdad del despliegue.
- Mantener [`pi_deployment_progress.md`](pi_deployment_progress.md) para el lado Pi.
- Actualizar `README.md`: dev local (`docker compose up`), prod (push → Actions),
  URL del dashboard (DNS del ALB, fija).
- **Limpieza post-entrega** (ya anotada en el doc de la Pi): `desired-count=0` en
  ambos servicios, borrar ALB/TG/RDS/ECR, eliminar cert ACM. Agregar acá un
  bloque "teardown" con los comandos cuando se decida.

---

## Orden recomendado
1. **Fase 1 (ALB)** — máximo impacto, desacopla todo de las IPs.
2. **Fase 2 (imágenes prod)** — para no depender de `npm run dev` en ECS.
3. **Fase 3 (GitHub Actions)** — automatiza una vez que 1 y 2 estén estables.
4. **Fase 4** — en paralelo, ir documentando cada fase al cerrarla.

## Registro de decisiones
- **2026-06-08** Cert: **self-signed** (no hay dominio). Revisar si aparece dominio.
- **2026-06-08** Endpoint estable: **ALB** (no Elastic IP — no aplica a Fargate awsvpc).
- **2026-06-08** Frontend→backend: vía **ALB same-origin `/api`** (no IP hardcodeada).
- **2026-06-15** Fase 1 (ALB) **desplegada y verificada** (3 curl 1.6 OK). Cert con
  CN FQDN (`somnolence-demo.local`) por requisito de ACM/ELB.
- **2026-06-15** Fase 2 frontend **hecha**: imagen prod standalone, same-origin.
  Bake `NEXT_PUBLIC_API_URL=""` (no DNS horneado). Código en `feat/frontend-prod-build`.
- **2026-06-15** Entornos AWS: **uno solo** (`main` = prod; `develop` se prueba
  local con compose). No se monta dev+prod separados en AWS (overkill académico).
