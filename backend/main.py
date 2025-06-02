# livestream-w2-gaules/backend/main.py

import os
import multiprocessing
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.download_models import download_all_models
from capture.recorder import start_capture
from pipeline.worker import worker_loop

# —— CONFIGURAÇÃO DO LOGGER —— 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("backend")


# —— GARANTE QUE AS PASTAS EXISTAM ANTES DE MONTAR O StaticFiles —— 
# (isso evita RuntimeError quando o container sobe)
os.makedirs("hls", exist_ok=True)
os.makedirs("audio_segments", exist_ok=True)


# —— INICIALIZA O FastAPI E O CORS —— 
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# —— BAIXA/CHECA MODEL WHISPER NO STARTUP —— 
download_all_models()


# —— ROTAS DE API —— 

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia pipeline para:
      1) Capturar áudio da Twitch (streamlink → ffmpeg → .wav em audio_segments/{channel}/).
      2) Worker em processo separado que faz transcrição, tradução, TTS e HLS em hls/{channel}/{lang}/.
    """
    logger.info(f"[backend] Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # 1) Garante que exista pasta para áudio bruto
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)
    logger.info(f"[backend] Diretório de áudio garantido: {audio_dir}")

    # 2) Garante que exista pasta para HLS
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)
    logger.info(f"[backend] Diretório HLS garantido: {hls_dir}")

    # 3) Dispara captura em background (streamlink→ffmpeg)
    background_tasks.add_task(_run_recorder, channel, audio_dir)

    # 4) Dispara worker em outro processo
    background_tasks.add_task(_run_worker, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    (Opcional) Endpoint para parar captura de um canal específico.
    Ainda não implementado.
    """
    logger.info(f"[backend] /stop solicitado para canal='{channel}'. (não implementado)")
    return {"status": "parado", "channel": channel}


# —— FUNÇÕES AUXILIARES —— 

def _run_recorder(channel_name: str, output_dir: str):
    """
    Roda start_capture em foreground (que, por sua vez, dispara streamlink|ffmpeg).
    """
    logger.info(f"[recorder] Diretório de saída garantido: {output_dir}")
    start_capture(channel_name, output_dir)
    # start_capture só retorna quando o processo de ffmpeg/streamlink encerrar.


def _run_worker(audio_dir: str, lang: str):
    """
    Cria um processo separado para o worker_loop,
    que monitora audio_dir e gera HLS em paralelo.
    """
    p = multiprocessing.Process(target=worker_loop, args=(audio_dir, lang))
    p.daemon = True
    p.start()
    logger.info(f"[backend] Processo de worker iniciado com PID {p.pid}.")


# —— APÓS DEFINIR TODAS AS ROTAS, MONTAMOS OS ARQUIVOS ESTÁTICOS —— 

# 1) "/hls" serve os arquivos HLS gerados: .m3u8 + .ts
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# 2) "/" serve o build do React (frontend/dist)
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
