# livestream-w2-gaules/backend/main.py

import os
import multiprocessing
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importa o recorder e worker
from capture.recorder import start_capture
from pipeline.worker import worker_loop

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

# Ao iniciar, garante as pastas estáticas existirem
os.makedirs("hls", exist_ok=True)
os.makedirs("audio_segments", exist_ok=True)

# Monta o diretório 'hls' para servir os arquivos HLS (m3u8 e .ts)
app.mount("/hls", StaticFiles(directory="hls"), name="hls")
# Monta o diretório 'frontend/dist' para servir o build do React
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura + worker em processos separados:
      - start_capture: grava áudio bruto em segmentos .wav
      - worker_loop: transcreve, traduz, sintetiza com Speechify e gera HLS
    """
    logger.info(f"[backend] Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # 1) Cria a pasta de áudio bruto (segmentos .wav)
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)
    logger.info(f"[backend] Diretório de áudio garantido: {audio_dir}")

    # 2) Cria a pasta onde o HLS será gerado
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)
    logger.info(f"[backend] Diretório HLS garantido: {hls_dir}")

    # 3) Inicia o processo de captura (streamlink + ffmpeg) e o worker
    #    Vamos usar multiprocessing.Process para que fiquem fora do contexto do FastAPI
    p_capture = multiprocessing.Process(target=start_capture, args=(channel, audio_dir), daemon=True)
    p_capture.start()
    logger.info(f"[backend] [backend] Processo de captura iniciado com PID {p_capture.pid}.")

    p_worker = multiprocessing.Process(target=worker_loop, args=(audio_dir, lang), daemon=True)
    p_worker.start()
    logger.info(f"[backend] [backend] Processo de worker iniciado com PID {p_worker.pid}.")

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    (Opcional) Endpoint para parar captura/worker; pode ser implementado conforme necessidade.
    """
    return {"status": "parado", "channel": channel}
