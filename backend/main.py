# backend/main.py

import os
import asyncio
from queue import Queue
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from pipeline.worker import worker_loop
from capture.recorder import start_capture
from backend.download_models import download_all_models

app = FastAPI()

# **1)** Fila de logs: mapeia "<channel>_<lang>" → Queue()
log_queues: dict[str, Queue] = {}

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baixa/verifica o modelo Whisper ao iniciar
download_all_models()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    1) Garante diretórios:
       - áudio cru em audio_segments/{channel}/
       - HLS em hls/{channel}/{lang}/
    2) Cria uma Queue() específica para este canal+idioma e guarda em log_queues.
    3) Dispara duas tarefas em background:
       - start_capture (que grava stick de .wav)
       - worker_loop (que produz HLS e envia mensagens à fila)
    """
    # 1.1) Diretório de áudio cru
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # 1.2) Diretório de saída HLS
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # 2) Cria/limpa a fila de logs para este canal+idioma
    key = f"{channel}_{lang}"
    q = Queue()
    log_queues[key] = q

    # 3) Agrega as tarefas em background, passando também a Queue de logs
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, audio_dir, lang, q)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    (Você pode implementar lógica de parada aqui, se quiser.)
    """
    return {"status": "parado", "channel": channel}


@app.get("/logs/{channel}/{lang}")
async def stream_logs(channel: str, lang: str):
    """
    SSE endpoint: abre uma conexão text/event-stream e envia cada nova linha que
    o worker_loop colocar na fila log_queues["channel_lang"].
    """
    key = f"{channel}_{lang}"
    if key not in log_queues:
        return {"detail": "não há logs para este canal+idioma"}

    q: Queue = log_queues[key]

    async def event_generator():
        """
        A cada `q.get()` (bloqueante), converte para SSE e devolve ao client.
        """
        loop = asyncio.get_event_loop()
        while True:
            # roda o bloqueio da queue em executor para não travar o event loop
            message = await loop.run_in_executor(None, q.get)
            yield f"data: {message}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Monta pasta HLS para servir .m3u8 / .ts
os.makedirs("hls", exist_ok=True)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta build do React em “/”
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
