# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.download_models import download_all_models
from capture.recorder import start_capture
from pipeline.worker import worker_loop

app = FastAPI()

# Permite CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baixa/verifica o modelo Whisper ao iniciar
download_all_models()

# Garante que a pasta 'hls' exista antes de montá-la
os.makedirs("hls", exist_ok=True)

# Monta o diretório 'hls' para servir arquivos HLS (.m3u8 / .ts)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta o build React em '/'
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # Inicia captura e worker em segundo plano
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    return {"status": "parado", "channel": channel}
