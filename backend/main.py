# livestream-w2-gaules/backend/main.py

import os
import multiprocessing
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Baixa/verifica o modelo Whisper ao iniciar
from backend.download_models import download_all_models

# Captura de áudio da Twitch
from capture.recorder import start_capture

# Worker que faz transcrição, tradução, TTS (Speechify) e HLS
from pipeline.worker import worker_loop

app = FastAPI()

# CORS (ajuste se necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baixa/verifica o modelo Whisper
download_all_models()

# Garante que a pasta 'hls' exista antes de montar
os.makedirs("hls", exist_ok=True)

# Monta 'hls' para servir arquivos HLS (.m3u8 e .ts)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta o frontend compilado
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura + worker:
      - start_capture grava segmentos WAV em audio_segments/{channel}
      - worker_loop transcreve, traduz, TTS (Speechify) e gera HLS em hls/{channel}/{lang}
    """
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # Dispara captura em background
    background_tasks.add_task(start_capture, channel, audio_dir)

    # Dispara worker em background
    # NOTE: usamos multiprocessing para não bloquear o thread do FastAPI
    process = multiprocessing.Process(target=worker_loop, args=(audio_dir, lang))
    process.daemon = True
    process.start()

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Implementar se necessário para parar captura/worker.
    """
    return {"status": "parado", "channel": channel}
