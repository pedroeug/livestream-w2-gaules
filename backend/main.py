# backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from capture.recorder import start_capture
from pipeline.worker import worker_loop

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Antes de montar StaticFiles, criamos a pasta raiz “hls”
os.makedirs("hls", exist_ok=True)

# Monta “/hls” para servir os arquivos HLS
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    # Cria pasta de áudio bruto
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Cria pasta onde o HLS irá aparecer
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # Inicia captura e worker em background
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}
