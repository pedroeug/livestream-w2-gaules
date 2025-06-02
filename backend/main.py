# livestream-w2-gaules/backend/main.py

import os
import multiprocessing
import subprocess
import shlex
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

# importar funções auxiliares (ajuste caminhos se necessário)
from backend.download_models import download_all_models
from capture.recorder import start_capture
from pipeline.worker import worker_loop

# configurar logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("backend")

app = FastAPI()

# 1) Habilitar CORS (se o front fizer requisições AJAX, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) Health check simples
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 3) Rota para iniciar captura + pipeline
@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia em background:
      1) O processo de captura (streamlink → ffmpeg → arquivos .wav em audio_segments/{channel}/).
      2) Um worker separado que processa esses .wav (Whisper, traduções, TTS, HLS em hls/{channel}/{lang}/).
    """

    logger.info(f"[backend] Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # 3.1) Diretório de áudio bruto
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)
    logger.info(f"[backend] Diretório de saída garantido: {audio_dir}")

    # 3.2) Diretório onde o HLS será servido: hls/{channel}/{lang}/index.m3u8
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)
    logger.info(f"[backend] Diretório HLS garantido: {hls_dir}")

    # 3.3) Iniciar o processo de captura em background
    # Note: start_capture roda em forma de “subprocess” (streamlink|ffmpeg)
    background_tasks.add_task(_run_recorder, channel, audio_dir)

    # 3.4) Iniciar o worker em background
    background_tasks.add_task(_run_worker, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Endpoint placeholder – se quiser implementar parada de captura, pode registrar PID e matar aqui.
    """
    logger.info(f"[backend] Stop solicitado para canal='{channel}'. (não implementado)")
    return {"status": "parado", "channel": channel}


# 4) Auxiliares que realmente disparam subprocessos em paralelo

def _run_recorder(channel_name: str, output_dir: str):
    """
    Função que será executada dentro de BackgroundTasks.
    Recebe o channel_name e o diretório onde salvará segmentos .wav.
    """
    logger.info(f"[recorder] Diretório de saída garantido: {output_dir}")
    start_capture(channel_name, output_dir)
    # NOTE: start_capture só sai se o processo de ffmpeg/streamlink terminar.


def _run_worker(audio_dir: str, lang: str):
    """
    Função que será executada dentro de BackgroundTasks.
    Chama worker_loop dentro de um processo separado (multiprocessing), para não bloquear.
    """
    # Usamos multiprocessing.Process apenas para demonstrar que criamos um processo separado.
    p = multiprocessing.Process(target=worker_loop, args=(audio_dir, lang))
    p.daemon = True
    p.start()
    logger.info(f"[backend] Processo de worker iniciado com PID {p.pid}.")


# 5) Após todas as rotas de API, monte os arquivos estáticos

# 5.1) Montar o diretório “hls” (onde o worker grava .ts e index.m3u8)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# 5.2) Montar o front‐end compilado (Vite/React → pasta frontend/dist)
#      A raiz “/” agora retorna index.html de dist/ e serve todos os assets.
#      IMPORTANTE: faça isso **dePOIS** de declarar as rotas acima.
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
