# livestream-w2-gaules/backend/main.py

import os
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.download_models import download_all_models
from capture.recorder import start_capture
from pipeline.worker import worker_loop

# —————————————————————————————————————————————————————————————————————————————
# CONFIGURAÇÃO DE LOGGING (opcional, mas recomendado para depuração)
# —————————————————————————————————————————————————————————————————————————————
logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# —————————————————————————————————————————————————————————————————————————————
# GARANTE CRIAÇÃO DA PASTA "hls/" ANTES DE TUDO
# —————————————————————————————————————————————————————————————————————————————
os.makedirs("hls", exist_ok=True)
logger.info("Pasta 'hls/' criada/verificada antes de montar StaticFiles.")

app = FastAPI()

# CORS (ajuste allow_origins se quiser restringir)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# —————————————————————————————————————————————————————————————————————————————
# EVENTO DE STARTUP: baixar/verificar modelo Whisper
# —————————————————————————————————————————————————————————————————————————————
@app.on_event("startup")
async def on_startup():
    download_all_models()
    logger.info("Modelos Whisper verificados/baixados no startup.")


# —————————————————————————————————————————————————————————————————————————————
# MONTAGEM DOS ARQUIVOS HLS (os .m3u8 e .ts gerados pelo pipeline)
# Note que já criamos 'hls/' acima, então não haverá erro de “directory does not exist”.
# —————————————————————————————————————————————————————————————————————————————
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")


# —————————————————————————————————————————————————————————————————————————————
# ENDPOINTS DA API
# —————————————————————————————————————————————————————————————————————————————

@app.get("/health")
async def health_check():
    """
    Health check para verificar se o backend está rodando.
    """
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura e processamento em segundo plano:
      - start_capture grava WAVs em "audio_segments/{channel}/…"
      - worker_loop processa, faz transcrição, tradução, TTS e gera HLS em "hls/{channel}/{lang}/…"
    """
    if not channel:
        raise HTTPException(status_code=400, detail="Canal não informado.")
    if lang not in ("en", "pt", "es"):
        raise HTTPException(status_code=400, detail="Idioma não suportado.")

    # 1) Pasta de gravação dos segmentos de áudio brutos (WAV):
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # 2) Pasta para armazenar os WAVs/TTS/concat gerados (processados):
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # 3) Pasta de saída final dos arquivos HLS gerados:
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    logger.info(f"Iniciando captura para canal '{channel}', idioma '{lang}'.")
    # Dispara a captura de áudio (em background):
    background_tasks.add_task(start_capture, channel, audio_dir)
    # Dispara o worker (transcrição/tradução/TTS/HLS) em background:
    background_tasks.add_task(worker_loop, audio_dir, processed_dir, lang, hls_dir)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Para a captura e o processamento (se implementado stop_capture, etc).
    Por enquanto, apenas devolve um JSON.
    """
    return {"status": "parado", "channel": channel}


# —————————————————————————————————————————————————————————————————————————————
# SERVIÇÃO DO FRONTEND (VITE BUILD) DE FORMA A GARANTIR QUE /start NÃO SEJA SOBRESCRITO
# —————————————————————————————————————————————————————————————————————————————

# 1) Rota raiz “/” devolve o index.html gerado por Vite
@app.get("/")
async def serve_index():
    index_path = os.path.join("frontend", "dist", "index.html")
    if not os.path.isfile(index_path):
        raise HTTPException(status_code=404, detail="Arquivo index.html não encontrado")
    return FileResponse(index_path)


# 2) Monta apenas a pasta "frontend/dist/assets" em "/assets"
#    (o Vite normalmente gera /assets/… dentro de dist)
assets_dir = os.path.join("frontend", "dist", "assets")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
else:
    logger.warning(f"Diretório de assets não existe: {assets_dir}")


# —————————————————————————————————————————————————————————————————————————————
# FIM DO ARQUIVO
# —————————————————————————————————————————————————————————————————————————————
