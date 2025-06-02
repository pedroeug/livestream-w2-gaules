# livestream-w2-gaules/backend/main.py

import os
import subprocess
import logging

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importa o download de modelos Whisper (caso esteja usando)
from backend.download_models import download_all_models

# Importa a captura de áudio da Twitch
from capture.recorder import start_capture

# Importa o worker (que agora usa Speechify via HTTP)
from pipeline.worker import worker_loop

logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

app = FastAPI()

# 1) Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 3) Endpoint para iniciar pipeline
@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura e processamento em segundo plano:
      - start_capture grava áudio da Twitch em segmentos de 10s.
      - worker_loop fica monitorando e gera HLS em hls/{channel}/{lang}/.
    """
    logger.info(f"[backend] Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # Diretório de áudio bruto
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Diretório de HLS (servido staticamente)
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # (a) Inicia o processo de captura via subprocesso (streamlink + ffmpeg)
    proc_capture = subprocess.Popen(
        [
            "python3", "-c",
            f"from capture.recorder import start_capture; start_capture('{channel}', '{audio_dir}')"
        ]
    )
    logger.info(f"[backend] Processo de captura iniciado com PID {proc_capture.pid}.")

    # (b) Inicia o worker_loop em outro subprocesso
    proc_worker = subprocess.Popen(
        [
            "python3", "-c",
            f"from pipeline.worker import worker_loop; worker_loop('{audio_dir}', '{lang}')"
        ]
    )
    logger.info(f"[backend] Processo de worker iniciado com PID {proc_worker.pid}.")

    return {"status": "iniciado", "channel": channel, "lang": lang}


# 4) Rota de "stop" (ainda placeholder)
@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    return {"status": "parado", "channel": channel}


# 5) Monta o diretório "hls" para servir arquivos HLS (m3u8 + .ts)
os.makedirs("hls", exist_ok=True)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")


# 6) Monta o React compilado em "/" **APÓS** todas as rotas acima
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


# 7) (Opcional) Baixa/verifica modelos Whisper no startup
download_all_models()
