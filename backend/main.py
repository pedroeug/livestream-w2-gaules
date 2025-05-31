# livestream-w2-gaules/backend/main.py

import os
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# Importa o download de modelos Whisper (arquivo: backend/download_models.py)
from backend.download_models import download_all_models

# Importa a função que inicia a captura via streamlink+ffmpeg (arquivo: capture/recorder.py)
from capture.recorder import start_capture

# Importa o wrapper de thread para o worker
from pipeline.worker_thread import start_worker_thread

app = FastAPI()

# -------------------------------------------------------------
# 1) Configurações globais (CORS, etc.)
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permite qualquer origem (ajuste se necessário)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# 2) Health check
# -------------------------------------------------------------
@app.get("/health")
async def health_check():
    """
    Health check para verificar se o backend está no ar.
    """
    logger.info("Health check solicitado")
    return {"status": "ok"}


# -------------------------------------------------------------
# 3) Rota para iniciar captura e processamento
# -------------------------------------------------------------
@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura e processamento em segundo plano:
      - start_capture grava áudio do canal Twitch em segmentos de 10s.
      - worker_loop transcreve, traduz, sintetiza e monta HLS.
    """
    logger.info(f"Iniciando stream para canal {channel} com idioma {lang}")
    
    # 3.1) Cria pasta para armazenar segmentos de áudio brutos
    audio_dir = os.path.join("audio_segments", channel)
    try:
        os.makedirs(audio_dir, exist_ok=True)
        logger.info(f"Diretório de áudio criado/verificado: {audio_dir}")
    except Exception as e:
        logger.error(f"Falha ao criar pasta audio_segments/{channel}: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao criar pasta audio_segments/{channel}: {e}")

    # 3.2) Cria pasta onde serão gerados os arquivos HLS: hls/{channel}/{lang}/
    hls_dir = os.path.join("hls", channel, lang)
    try:
        os.makedirs(hls_dir, exist_ok=True)
        logger.info(f"Diretório HLS criado/verificado: {hls_dir}")
    except Exception as e:
        logger.error(f"Falha ao criar pasta hls/{channel}/{lang}: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao criar pasta hls/{channel}/{lang}: {e}")

    # 3.3) Dispara as duas tarefas em background:
    #      1) start_capture(channel, audio_dir) –> gera segment_XXX.wav em audio_segments/channel/
    #      2) worker_loop(audio_dir, lang) –> monitora audio_segments/channel/ e gera HLS em hls/channel/lang/
    
    # Configurar variáveis de ambiente para o worker
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    deepl_api_key = os.getenv("DEEPL_API_KEY")
    
    if elevenlabs_api_key and elevenlabs_voice_id:
        logger.info(f"ElevenLabs configurado: API Key {elevenlabs_api_key[:5]}...{elevenlabs_api_key[-3:]} e Voice ID {elevenlabs_voice_id}")
    else:
        logger.warning("AVISO: ELEVENLABS_API_KEY ou ELEVENLABS_VOICE_ID não definido. TTS será pulado.")
    
    if deepl_api_key:
        logger.info(f"DeepL API Key configurada: {deepl_api_key[:5]}...{deepl_api_key[-3:]}")
    else:
        logger.warning("AVISO: DEEPL_API_KEY não definido. Tradução será pulada.")
    
    # Iniciar captura de áudio
    capture_process = start_capture(channel, audio_dir)
    if capture_process:
        logger.info(f"Processo de captura iniciado com PID {capture_process.pid}")
    else:
        logger.error("Falha ao iniciar processo de captura")
        raise HTTPException(status_code=500, detail="Falha ao iniciar processo de captura")
    
    # Iniciar worker em thread separada
    worker_thread = start_worker_thread(audio_dir, lang)
    logger.info("Worker thread iniciada")

    return {
        "status": "iniciado", 
        "channel": channel, 
        "lang": lang,
        "hls_url": f"/hls/{channel}/{lang}/index.m3u8"
    }


# -------------------------------------------------------------
# 4) Rota para parar captura/processing (placeholder)
# -------------------------------------------------------------
@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Placeholder para parar captura e processamento de um canal.
    (Ainda não implementado adequadamente; apenas retorna status.)
    """
    logger.info(f"Solicitação para parar stream do canal {channel}")
    return {"status": "parado", "channel": channel}


# -------------------------------------------------------------
# 5) Na inicialização, baixa/verifica o modelo Whisper e garante pasta HLS
# -------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    # 5.1) Baixa/verifica o modelo Whisper (podendo demorar alguns segundos)
    logger.info("Baixando/verificando modelos Whisper...")
    download_all_models()
    logger.info("Modelos Whisper prontos.")

    # 5.2) Garante que exista a pasta "hls" na raiz (para servir os arquivos HLS)
    try:
        os.makedirs("hls", exist_ok=True)
        logger.info("Diretório HLS principal criado/verificado")
    except Exception as e:
        logger.error(f"Não foi possível criar pasta 'hls': {e}")



# -------------------------------------------------------------
# 6) Montagem dos diretórios como "arquivos estáticos"
#
#    IMPORTANTE: crie as rotas "dinâmicas" ANTES destes mounts.
# -------------------------------------------------------------
# 6.1) Monta a pasta "hls" na rota "/hls" para servir .m3u8 e .ts
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# 6.2) Monta a pasta "frontend/dist" na raiz para servir o React
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
