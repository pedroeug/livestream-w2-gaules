#!/bin/bash

set -e

echo "[1/4] Criando pastas de modelos se necessário..."
mkdir -p vocoder/saved_models
mkdir -p encoder/saved_models
mkdir -p synthesizer/saved_models/logs-pretrained/taco_pretrained

echo "[2/4] Baixando arquivos de modelos..."
# Vocoder
wget -O vocoder/saved_models/pretrained.pt "https://drive.google.com/uc?export=download&id=1Z1BO5j104CtHpwl3oVIvNRtbDqUXGdZ9"

# Encoder
wget -O encoder/saved_models/pretrained.pt "https://drive.google.com/uc?export=download&id=1ExOFjsWzkEciECIRDKO5VNRoGW4978Hm"

# Synthesizer
wget -O synthesizer/saved_models/logs-pretrained/taco_pretrained/checkpoint "https://drive.google.com/uc?export=download&id=1rSnF6oR-2MON_6-6oi0zlWU2vwkb9TPg"
wget -O synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.data-00000-of-00001 "https://drive.google.com/uc?export=download&id=1GLWwh4K-5D4Gmy6e0TqbYZ8UWYsCtqSv"
wget -O synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.index "https://drive.google.com/uc?export=download&id=1kWyLxdJS-gJ7SoaWEo7n9qx8G-WoU62E"
wget -O synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.meta "https://drive.google.com/uc?export=download&id=1bJ1WgBekNp_8sMzz6J7sp_eFXco_N-TE"

echo "[3/4] Iniciando o servidor..."
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT
