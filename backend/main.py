# livestream-w2-gaules/backend/main.py

import os
import multiprocessing
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

# Importa o download de modelos Whisper (já no seu projeto)
from backend.download_models import download_all_models

# Importa a captura de áudio da Twitch
from capture.recorder import start_capture

# Importa o worker que faz transcrição, tradução, síntese e HLS
from pipeline.worker import worker_loop

# Configura logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

# 1) Rotas de API + CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura (start_capture) e worker_loop em processos separados:
    - start_capture grava áudio em audio_segments/{channel}/segment_*.wav
    - worker_loop monitora e gera HLS em hls/{channel}/{lang}/index.m3u8
    """
    logger.info(f"[backend] Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # 1) Cria diretório de áudio bruto
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)
    logger.info(f"[backend] Diretório de áudio garantido: {audio_dir}")

    # 2) Cria diretório HLS
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)
    logger.info(f"[backend] Diretório HLS garantido: {hls_dir}")

    # 3) Dispara captura e worker em processos separados
    #    Usamos multiprocessing.Process para que não bloqueie a thread de FastAPI
    def _run_capture():
        logger.info(f"[backend] [recorder] Diretório de saída garantido: {audio_dir}")
        start_capture(channel, audio_dir)

    def _run_worker():
        worker_loop(audio_dir, lang)

    p1 = multiprocessing.Process(target=_run_capture)
    p1.daemon = True
    p1.start()
    logger.info(f"[backend] [backend] Processo de captura iniciado com PID {p1.pid}.")

    p2 = multiprocessing.Process(target=_run_worker)
    p2.daemon = True
    p2.start()
    logger.info(f"[backend] [backend] Processo de worker iniciado com PID {p2.pid}.")

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Endpoint placeholder para eventualmente parar captura e processamento.
    """
    # (implementação de parada ficaria aqui)
    return {"status": "parado", "channel": channel}


# 2) Somente depois de declarar todas as rotas, montamos o frontend estático
# Monta o diretório 'hls' para servir .m3u8 e .ts
os.makedirs("hls", exist_ok=True)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta o diretório do build do React (frontend/dist) 
# para servir HTML/JS/CSS em todas as outras rotas GET
os.makedirs("frontend/dist", exist_ok=True)
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

# 3) Download dos modelos Whisper na inicialização
download_all_models()
