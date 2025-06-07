#!/usr/bin/env bash

# Gera o frontend em produção caso a pasta dist não exista
if [ ! -d frontend/dist ]; then
  echo "Gerando build do frontend..."
  npm --prefix frontend install
  npm --prefix frontend run build
fi

uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
