# livestream-w2-gaules/backend/main.py

import os
import logging
import multiprocessing
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.download_models import download_all_models
from capture.recorder import start_capture
from pipeline.worker import worker_loop

# —————————————————————————————————————————————————————————————————————————————
# CONFIGURAÇÃO DE LOGGING
# —————————————————————————————————————————————————————————————————————————————
logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# —————————————————————————————————————————————————————————————————————————————
# GARANTE CRIAÇÃO DAS PASTAS NECESSÁRIAS PARA HLS E AUDIO_SEGMENTS
# —————————————————————————————————————————————————————————————————————————————
os.makedirs("hls", exist_ok=True)
os.makedirs("audio_segments", exist_ok=True)
logger.info("Pastas iniciais criadas/verificadas: 'hls/', 'audio_segments/'.")

app = FastAPI()

# —————————————————————————————————————————————————————————————————————————————
# CORS (ajuste allow_origins se quiser restringir)
# —————————————————————————————————————————————————————————————————————————————
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# —————————————————————————————————————————————————————————————————————————————
# EVENTO DE STARTUP: baixar/verificar modelos Whisper
# —————————————————————————————————————————————————————————————————————————————
@app.on_event("startup")
async def on_startup():
    download_all_models()
    logger.info("Modelos Whisper verificados/baixados no startup.")


# —————————————————————————————————————————————————————————————————————————————
# MONTAGEM DOS ARQUIVOS HLS 
# —————————————————————————————————————————————————————————————————————————————
# (Como já garantimos que 'hls/' existe acima, não haverá erro de "directory does not exist".)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")


# —————————————————————————————————————————————————————————————————————————————
# ENDPOINTS DA API
# —————————————————————————————————————————————————————————————————————————————

@app.get("/health")
async def health_check():
    """
    Health check para verificar se o backend está funcionando.
    """
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str):
    """
    Inicia captura e processamento em dois processos separados:
      1) start_capture() grava WAVs em "audio_segments/{channel}/…"
      2) worker_loop() processa WAVs, faz transcrição, tradução, TTS e gera HLS em "hls/{channel}/{lang}/…"
    """
    # Validações básicas
    if not channel:
        raise HTTPException(status_code=400, detail="Canal não informado.")
    if lang not in ("en", "pt", "es"):
        raise HTTPException(status_code=400, detail="Idioma não suportado. Use 'en', 'pt' ou 'es'.")

    # 1) Cria a pasta onde a captura (start_capture) vai gravar segmentos .wav
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # 2) Cria uma subpasta para arquivos “processados” (concat.mp3, dub wav/mp3, etc)
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # 3) Cria a pasta de saída HLS (m3u8 + .ts)
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    logger.info(f"Iniciando pipeline para canal='{channel}', lang='{lang}'.")

    # --- a) Inicia captura de áudio (streamlink→ffmpeg). 
    # Isso já dispara um subprocesso que fica rodando até ser parado externamente.
    capture_proc = multiprocessing.Process(
        target=start_capture,
        args=(channel, audio_dir),
        daemon=True
    )
    capture_proc.start()
    logger.info(f"[backend] Processo de captura iniciado com PID {capture_proc.pid}.")

    # --- b) Inicia o worker_loop num processo separado (runs forever).
    worker_proc = multiprocessing.Process(
        target=worker_loop,
        args=(audio_dir, processed_dir, lang, hls_dir),
        daemon=True
    )
    worker_proc.start()
    logger.info(f"[backend] Processo de worker iniciado com PID {worker_proc.pid}.")

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Aqui você pode implementar lógica para matar processos de captura e worker do canal.
    No momento, apenas devolve status JSON.
    """
    return {"status": "parado", "channel": channel}


# —————————————————————————————————————————————————————————————————————————————
# SERVE O FRONTEND (build do Vite) SEM INTERFERIR NAS ROTAS /start E /health
# —————————————————————————————————————————————————————————————————————————————

# 1) Rota raiz ("/") devolve explicitamente o index.html gerado por Vite:
@app.get("/")
async def serve_index():
    index_path = os.path.join("frontend", "dist", "index.html")
    if not os.path.isfile(index_path):
        logger.error(f"index.html não encontrado em {index_path}")
        raise HTTPException(status_code=404, detail="Arquivo index.html não encontrado")
    return FileResponse(index_path)


# 2) Monta apenas a pasta "frontend/dist/assets" em "/assets"
assets_dir = os.path.join("frontend", "dist", "assets")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    logger.info(f"Montando assets estáticos em /assets a partir de {assets_dir}")
else:
    logger.warning(f"Diretório de assets não existe: {assets_dir}")


# —————————————————————————————————————————————————————————————————————————————
# FIM DE backend/main.py
# —————————————————————————————————————————————————————————————————————————————
