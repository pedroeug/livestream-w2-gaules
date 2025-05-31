# livestream-w2-gaules/backend/main.py

import os
import subprocess
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.download_models import download_all_models
from capture.recorder import start_capture
from pipeline.worker import worker_loop

logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ———————— GARANTE CRIAÇÃO DA PASTA HLS ANTES DE MONTAR ————————
os.makedirs("hls", exist_ok=True)
logger.info("Pasta 'hls/' criada/verificada antes de montar StaticFiles.")

@app.on_event("startup")
async def on_startup():
    # Baixa/verifica modelo Whisper
    download_all_models()
    logger.info("Modelos Whisper verificados/baixados no startup.")

# Monta os arquivos HLS (m3u8 e .ts):
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta o build estático do React (frontend/dist)
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    if not channel:
        raise HTTPException(status_code=400, detail="Canal não informado.")
    if lang not in ("en", "pt", "es"):
        raise HTTPException(status_code=400, detail="Idioma não suportado.")

    # pasta para gravação dos WAVs
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # pasta para armazenar arquivos processados (concat.mp3, clones, etc.)
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # pasta destino dos HLS finalizados
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    logger.info(f"Iniciando captura para canal '{channel}', idioma '{lang}'.")
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, audio_dir, processed_dir, lang, hls_dir)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    return {"status": "parado", "channel": channel}
