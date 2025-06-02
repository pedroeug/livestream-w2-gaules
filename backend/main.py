# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import subprocess

# Importa o download de modelos Whisper (se ainda for necessário)
from backend.download_models import download_all_models

# Importa a captura de áudio da Twitch
from capture.recorder import start_capture

# Importa o worker que faz transcrição, tradução, síntese e HLS
from pipeline.worker import worker_loop

logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baixa/verifica o modelo Whisper ao iniciar (se você ainda usa o download_all_models)
download_all_models()

# Garante que a pasta 'hls' exista (servida estaticamente)
os.makedirs("hls", exist_ok=True)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Servir o frontend compilado pelo Vite
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Ao receber esta rota, iniciamos:
      - start_capture em background (gera WAVs em audio_segments/{channel}/).
      - worker_loop em outro processo (processa e gera HLS).
    """
    logger.info(f"[backend] Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # Diretório de áudio bruto
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Diretório de HLS (servido staticamente)
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # Inicia captura (subprocesso ffmpeg + streamlink)
    proc_capture = subprocess.Popen(
        [
            "python3", "-c",
            f"from capture.recorder import start_capture; start_capture('{channel}', '{audio_dir}')"
        ]
    )
    logger.info(f"[backend] Processo de captura iniciado com PID {proc_capture.pid}.")

    # Inicia worker_loop em outro processo
    proc_worker = subprocess.Popen(
        [
            "python3", "-c",
            f"from pipeline.worker import worker_loop; worker_loop('{audio_dir}', '{lang}')"
        ]
    )
    logger.info(f"[backend] Processo de worker iniciado com PID {proc_worker.pid}.")

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Aqui você poderia implementar a lógica para encerrar o ffmpeg/worker.
    Por ora, deixamos como placeholder.
    """
    return {"status": "parado", "channel": channel}
