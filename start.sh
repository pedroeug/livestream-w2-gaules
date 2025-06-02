#!/usr/bin/env bash

# arquivo start.sh na raiz do projeto
# Inicia o Uvicorn com FastAPI usando a porta 8000

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
