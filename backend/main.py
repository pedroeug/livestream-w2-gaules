# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importa o download de modelos Whisper
from backend.download_models import download_all_models

# Importa a captura de áudio da Twitch
from capture.recorder import start_capture

# Importa o worker que faz transcrição, tradução, síntese e HLS
from pipeline.worker import worker_loop

app = FastAPI()

# Configura CORS para permitir qualquer origem (ajuste se necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baixa/verifica o modelo Whisper ao iniciar
download_all_models()

# Garante que a pasta 'hls' exista (onde o pipeline vai gravar os arquivos HLS)
os.makedirs("hls", exist_ok=True)

# Monta o diretório 'hls' para servir os arquivos HLS (m3u8 e .ts)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta o diretório 'frontend/dist' para servir os arquivos estáticos do React
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    """
    Health check para verificar se o backend está funcionando.
    """
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura e processamento em segundo plano:
    - start_capture grava áudio da Twitch em segmentos de 10s.
    - worker_loop transcreve, traduz, sintetiza e monta HLS.
    """
    # Pasta onde serão colocados os segmentos de áudio brutos
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Pasta onde o HLS será gerado: hls/{channel}/{lang}/index.m3u8, etc.
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # Dispara tarefas em background:
    # 1) Captura áudio em 'audio_segments/{channel}'
    # 2) Worker processa e grava HLS em 'hls/{channel}/{lang}'
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Placeholder para parar captura e processamento de um canal.
    """
    return {"status": "parado", "channel": channel}
