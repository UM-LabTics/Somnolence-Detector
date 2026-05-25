#!/bin/sh
# entrypoint.sh — Puente entre Secrets Manager y el código del backend.
# Fargate inyecta el contenido de los certificados como variables de entorno.
# Este script los escribe a archivos en disco antes de arrancar uvicorn,
# porque paho-mqtt (tls_set) necesita rutas a archivos, no texto.

set -e

CERT_DIR=/tmp/certs
mkdir -p "$CERT_DIR"

# Escribir cada certificado desde su variable de entorno a un archivo.
# Las variables *_CONTENT las inyecta Fargate desde Secrets Manager.
printf '%s' "$MQTT_CA_CERT_CONTENT"     > "$CERT_DIR/AmazonRootCA1.pem"
printf '%s' "$MQTT_CLIENT_CERT_CONTENT" > "$CERT_DIR/device-cert.pem.crt"
printf '%s' "$MQTT_CLIENT_KEY_CONTENT"  > "$CERT_DIR/device-private.pem.key"

chmod 600 "$CERT_DIR"/*

echo "entrypoint: certificados escritos en $CERT_DIR"

# Arrancar el servidor. exec reemplaza el proceso del shell por uvicorn,
# para que las senales (parada del contenedor) lleguen bien a la app.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000