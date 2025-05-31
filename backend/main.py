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

# Monta o diretório 'frontend/dist' para servir arquivos estáticos do React
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
    # Cria pasta para salvar segmentos de áudio brutos
    output_dir = os.path.join("audio_segments", channel)
    os.makedirs(output_dir, exist_ok=True)

    # Dispara tarefas em background
    background_tasks.add_task(start_capture, channel, output_dir)
    background_tasks.add_task(worker_loop, output_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Placeholder para parar captura e processamento de um canal.
    """
    return {"status": "parado", "channel": channel}
