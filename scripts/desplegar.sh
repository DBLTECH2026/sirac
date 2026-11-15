#!/usr/bin/env bash
# Despliegue en el VPS (lo ejecuta GitHub Actions por SSH después de que pasan las pruebas).
# Construye las imágenes, levanta los contenedores y verifica la salud de la API con la versión nueva.
# Si la verificación falla, vuelve automáticamente a la versión anterior (rollback).
set -euo pipefail
cd /opt/sirac
PREV="${PREV:-$(git rev-parse HEAD)}"
export GIT_SHA="$(git rev-parse --short HEAD)"
echo "> Desplegando $GIT_SHA (versión anterior: ${PREV:0:7})"

docker compose build --pull
docker compose up -d --remove-orphans

for i in $(seq 1 40); do
  if curl -fsS --max-time 5 https://sirac.dbltech.tech/api/salud | grep -q "\"version\": \"$GIT_SHA\""; then
    echo "OK: SIRAC $GIT_SHA en línea (intento $i)"
    docker image prune -f >/dev/null
    exit 0
  fi
  sleep 5
done

echo "ERROR: la verificación de salud falló. Vuelvo a ${PREV:0:7}"
git reset --hard "$PREV"
export GIT_SHA="$(git rev-parse --short HEAD)"
docker compose build && docker compose up -d
exit 1
