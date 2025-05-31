#!/usr/bin/env bash
#
# start.sh
# Script que o Docker vai executar para iniciar o uvicorn
# (Garantindo que a variável $PORT seja respeitada.)

set -e

echo "=== Iniciando Uvicorn ==="
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
