# backend/main.py

import asyncio
import logging
import os
import queue

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from capture.recorder import start_capture
from pipeline.worker_thread import start_worker_thread

app = FastAPI()

# → 1.1) Cria uma fila thread-safe para empilhar cada linha de log
log_queue: queue.Queue[str] = queue.Queue()

# → 1.2) Hook de logging que joga cada registro na fila
class QueueHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        log_queue.put(msg)

# Configuramos o logger do nosso backend para usar esse handler:
logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)
q_handler = QueueHandler()
q_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(q_handler)

# (Opcional) redirecione logs de outras bibliotecas ao mesmo logger:
logging.getLogger("uvicorn.access").handlers.clear()
logging.getLogger("uvicorn.access").addHandler(q_handler)
logging.getLogger("uvicorn.error").handlers.clear()
logging.getLogger("uvicorn.error").addHandler(q_handler)


# → 1.3) Endpoint SSE que consome a fila e envia cada linha como "data: <mensagem>\n\n"
@app.get("/logs/stream")
async def stream_logs(request: Request) -> StreamingResponse:
    """
    Retorna um fluxo SSE com cada linha de log que aparecer no backend.
    """
    async def event_generator():
        # Enquanto a conexão não for fechada pelo cliente...
        while True:
            # Se o cliente desconectar, abortamos.
            if await request.is_disconnected():
                break

            try:
                # bloqueia até que haja uma nova mensagem
                line = log_queue.get(timeout=0.1)
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue

            # regenera o evento no formato SSE
            yield f"data: {line}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Endpoint para iniciar a captura e o worker de dublagem
@app.post("/start/{channel}/{lang}")
async def start_pipeline(channel: str, lang: str):
    audio_dir = os.path.join("audio_segments", channel)
    start_capture(channel, audio_dir)
    start_worker_thread(audio_dir, lang, log_queue)
    logger.info(f"Pipeline iniciado para {channel} em {lang}")
    return JSONResponse(content={"status": "ok"})


# ——————————————————————————————
# (A seguir, o restante das suas rotas / mount de staticfiles / etc.)
# Por exemplo:
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")
# Monte o frontend gerado pelo Vite
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
# … resto do seu main.py …
