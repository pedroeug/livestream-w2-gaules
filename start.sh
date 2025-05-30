#!/bin/bash

set -e

echo "[1/3] Instalando dependências do gdown..."
pip install gdown

echo "[2/3] Baixando os modelos com gdown..."
python download_models.py

echo "[3/3] Iniciando o servidor..."
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT
