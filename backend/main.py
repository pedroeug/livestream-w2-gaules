# livestream-w2-gaules/backend/main.py

import os
import subprocess
import shlex
import multiprocessing
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Importa o download de modelos Whisper
from download_models import download_all_models

# Importa a captura de áudio da Twitch
from capture.recorder import start_capture

# Importa o worker que faz transcrição, tradução, síntese e HLS
from pipeline.worker import worker_loop

app = FastAPI()

# CORS (se precisar permitir front rodando de outro domínio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Antes de tudo: baixa/verifica os modelos Whisper uma vez
download_all_models()

# Garante que exista a pasta 'hls' e 'audio_segments' (senão StaticFiles cai)
os.makedirs("hls", exist_ok=True)
os.makedirs("audio_segments", exist_ok=True)

# 1) Monta a pasta 'hls' em /hls
app.mount("/hls", StaticFiles(directory="hls"), name="hls")

# 2) No nível raiz, montamos a pasta do React (frontend/dist) como estática,
#    mas também usamos uma rota coringa para devolver o index.html sempre que
#    o caminho não bater em nenhum arquivo existente.
app.mount(
    "/static",
    StaticFiles(directory="frontend/dist/static", html=False),
    name="static",
)

@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    """
    Rota coringa: se o arquivo solicitado existir em frontend/dist, devolve-o.
    Senão, devolve sempre frontend/dist/index.html (para que o React Router funcione).
    """
    # tenta servir diretamente o arquivo (por exemplo, /static/alguma-coisa.js)
    real_path = os.path.join("frontend/dist", full_path)
    if os.path.isfile(real_path):
        return FileResponse(real_path)

    # Caso contrário, devolve sempre o index.html
    return FileResponse(os.path.join("frontend/dist", "index.html"))


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura e processamento em segundo plano:
    - start_capture grava áudio da Twitch em segmentos de 10s.
    - worker_loop transcreve, traduz, sintetiza e monta HLS.
    """
    # Diretório onde estarão os WAVs brutos
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # Diretório onde o HLS será escrito: hls/{channel}/{lang}/index.m3u8
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # 1) Captura de áudio (streamlink → ffmpeg) roda em outro processo
    p_capture = multiprocessing.Process(
        target=start_capture, args=(channel, audio_dir), daemon=True
    )
    p_capture.start()
    app.logger = app.__dict__.get("logger", None)
    if app.logger:
        app.logger.info(f"[backend] Processo de captura iniciado com PID {p_capture.pid}")
    else:
        print(f"[backend] Processo de captura iniciado com PID {p_capture.pid}")

    # 2) Worker loop (Whisper → Tradução → Speechify → HLS) em outro processo
    p_worker = multiprocessing.Process(
        target=worker_loop, args=(audio_dir, lang), daemon=True
    )
    p_worker.start()
    if app.logger:
        app.logger.info(f"[backend] Processo de worker iniciado com PID {p_worker.pid}")
    else:
        print(f"[backend] Processo de worker iniciado com PID {p_worker.pid}")

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Ainda não implementado: parar captura/worker.
    """
    return {"status": "parado", "channel": channel}
