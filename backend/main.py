# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from multiprocessing import Process
import logging

# Importa download de modelos Whisper
from backend.download_models import download_all_models

# Importa captura e worker
from capture.recorder import start_capture
from pipeline.worker import worker_loop

# Configura logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baixa/verifica o modelo Whisper ao iniciar
download_all_models()

# Garante que a pasta 'hls' exista
os.makedirs("hls", exist_ok=True)

# Monta o diretório 'hls' para servir arquivos HLS (.m3u8 e .ts)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta o diretório 'frontend/dist' para servir o React build
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    """
    Health check para verificar se o backend está funcionando.
    """
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str):
    """
    Inicia captura e worker em processos separados.
    """
    logger.info(f"Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # Pasta onde serão colocados os segmentos de áudio brutos
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Pasta onde o HLS será gerado: hls/{channel}/{lang}/index.m3u8, etc.
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # 1) inicia processo de captura
    recorder_proc = Process(
        target=start_capture,
        args=(channel, audio_dir),
        daemon=True
    )
    recorder_proc.start()
    logger.info(f"[backend] Processo de captura iniciado com PID {recorder_proc.pid}.")

    # 2) inicia processo de worker
    worker_proc = Process(
        target=worker_loop,
        args=(audio_dir, lang),
        daemon=True
    )
    worker_proc.start()
    logger.info(f"[backend] Processo de worker iniciado com PID {worker_proc.pid}.")

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    (Opcional) Implante lógica para finalizar processos do canal.
    Por enquanto, apenas responde que parou.
    """
    logger.info(f"Parando pipeline para canal='{channel}'. (não implementado)")
    return {"status": "parado", "channel": channel}
