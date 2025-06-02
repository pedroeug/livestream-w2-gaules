# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from capture.recorder import start_capture
from pipeline.worker import worker_loop
import logging

# Configurações de log
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

# Permitir CORS de qualquer origem (ajuste se necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Garante que as pastas existam ao iniciar
os.makedirs("hls", exist_ok=True)
os.makedirs("audio_segments", exist_ok=True)

# Monta a pasta 'hls' para servir HLS (index.m3u8 e .ts)
app.mount("/hls", StaticFiles(directory="hls"), name="hls")

# Monta o build do React em '/'
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia a captura (ffmpeg + streamlink) e o loop de worker (transcrição, tradução e TTS).
    """
    logger.info(f"[backend] Chamando start_stream: canal='{channel}', lang='{lang}'")

    # 1) Diretório onde os WAVs brutos vão ficar:
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # 2) Diretório onde o HLS será gerado:
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # 3) Dispara em background as duas tarefas:
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, channel, audio_dir, lang)

    return {"status": "started", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Placeholder para parar a captura/worker (não implementado aqui).
    """
    logger.info(f"[backend] Chamou stop_stream para canal='{channel}'")
    return {"status": "stopped", "channel": channel}
