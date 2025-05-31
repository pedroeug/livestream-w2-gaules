# livestream-w2-gaules/backend/main.py

import os
import subprocess
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Importa o download de modelos Whisper
from backend.download_models import download_all_models

# Importa a captura de áudio da Twitch
from capture.recorder import start_capture

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backend.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("backend")

app = FastAPI()

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

# Garante que a pasta 'hls' exista
os.makedirs("hls", exist_ok=True)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # Inicia a captura como background task
    background_tasks.add_task(start_capture, channel, audio_dir)
    
    # Inicia o worker como processo separado para evitar bloqueio do backend
    logger.info(f"Iniciando worker em processo separado para {channel} e idioma {lang}")
    try:
        worker_cmd = [
            "python", "-c", 
            f"from pipeline.worker import worker_loop; worker_loop('{audio_dir}', '{lang}')"
        ]
        subprocess.Popen(worker_cmd)
        logger.info("Worker iniciado com sucesso em processo separado")
    except Exception as e:
        logger.error(f"Erro ao iniciar worker: {e}")
        return {"status": "erro", "message": str(e)}

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    return {"status": "parado", "channel": channel}


# Rota específica para servir o manifesto HLS com cabeçalhos CORS adequados
@app.get("/hls/{channel}/{lang}/index.m3u8")
async def get_hls_manifest(channel: str, lang: str):
    manifest_path = os.path.join("hls", channel, lang, "index.m3u8")
    
    if not os.path.exists(manifest_path):
        return {"error": "Manifesto HLS não encontrado"}
    
    return FileResponse(
        manifest_path,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )


# Rota específica para servir os segmentos TS com cabeçalhos CORS adequados
@app.get("/hls/{channel}/{lang}/{segment}.ts")
async def get_hls_segment(channel: str, lang: str, segment: str):
    segment_path = os.path.join("hls", channel, lang, f"{segment}.ts")
    
    if not os.path.exists(segment_path):
        return {"error": f"Segmento {segment}.ts não encontrado"}
    
    return FileResponse(
        segment_path,
        media_type="video/mp2t",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )


# Monta o diretório 'frontend/dist' (React)
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
