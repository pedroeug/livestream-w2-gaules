# backend/main.py

import os
import multiprocessing
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pipeline.worker import worker_loop
from capture.recorder import start_capture
from backend.download_models import download_all_models

app = FastAPI()

# 1) Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) Baixa/verifica o modelo Whisper ao iniciar
download_all_models()

# 3) Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# 4) Rota para iniciar o pipeline (POST)
@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura e processamento em segundo plano:
      - start_capture grava áudio da Twitch em segmentos de 10s em audio_segments/{channel}/
      - worker_loop transcreve, traduz, sintetiza e gera HLS em hls/{channel}/{lang}/
    """
    # Diretório de áudio cru
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Diretório onde o HLS será gerado
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # Adiciona as tarefas em background
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


# 5) Rota para parar (pode implementar lógica de parada depois)
@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    return {"status": "parado", "channel": channel}


# 6) Agora sim, monta a pasta “hls” para servir os .m3u8 e .ts
os.makedirs("hls", exist_ok=True)  # garante existência para não dar erro no mount
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# 7) Por fim, monta o build do React em “/”
#    – Observe que esse mount só aparece **depois** das rotas acima
app.mount(
    "/",
    StaticFiles(directory="frontend/dist", html=True),
    name="frontend"
)
