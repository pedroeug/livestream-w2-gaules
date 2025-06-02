# livestream-w2-gaules/backend/main.py

import os
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importa o download de modelos Whisper
from backend.download_models import download_all_models

# Importa a captura de áudio da Twitch
from capture.recorder import start_capture

# Importa o worker que faz transcrição, tradução, síntese e HLS
from pipeline.worker import worker_loop

# Configura logging básico para vermos as mensagens no console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

# Configura CORS para permitir qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ao iniciar, baixa/verifica modelos Whisper
download_all_models()

# Garante que as pastas existam
os.makedirs("hls", exist_ok=True)
os.makedirs("audio_segments", exist_ok=True)

# Monta /hls para servir playlists/segments HLS
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")
# Monta /audio_segments para servir o MP3 concat
app.mount("/audio_segments", StaticFiles(directory="audio_segments", html=False), name="audio")

# Monta o React compilado em /frontend/dist
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura + worker em background:
     - start_capture: grava wavs em audio_segments/{channel}/segment_###
     - worker_loop: processa, traduz, sintetiza e cria “processed/concat.mp3”
    """
    logger.info(f"[backend] Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # Cria pastas:
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Dentro de audio_segments/{channel}, cria subpasta “processed”:
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Dispara captura em processo separado:
    background_tasks.add_task(start_capture, channel, audio_dir)
    # Dispara worker (traduz+TTS) em paralelo:
    background_tasks.add_task(worker_loop, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Placeholder para parar captura/processamento.
    (Ainda não implementado)
    """
    return {"status": "parado", "channel": channel}
