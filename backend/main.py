# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from multiprocessing import Process
import logging
from dotenv import load_dotenv # Importar dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Ajuste de logging para exibir mensagens de INFO nos subprocessos
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("backend")

# Importa as funções de captura e worker
# from download_models import download_all_models # Comentado pois o arquivo não existe no repo
from capture.recorder import start_capture
from pipeline.worker import worker_loop

app = FastAPI()

# Configura CORS (ajuste allow_origins conforme necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baixa/verifica o modelo Whisper assim que o servidor sobe
# download_all_models() # Comentado pois a função não está definida

# Garante que as pastas necessárias existam
os.makedirs("hls", exist_ok=True)
os.makedirs("frontend/dist", exist_ok=True)

# --- Definição das Rotas da API --- 

@app.get("/health")
async def health_check():
    """
    Endpoint de health check para verificar se o backend está no ar.
    """
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_pipeline(channel: str, lang: str):
    """
    Inicia a captura de áudio da Twitch e o processamento em segundo plano:
      - start_capture grava segmentos .wav em audio_segments/{channel}.
      - worker_loop consome esses .wav, transcreve, traduz, sintetiza e gera HLS em hls/{channel}/{lang}.
    """

    logger.info(f"Iniciando pipeline para canal=\'{channel}\', lang=\'{lang}\'.")
    # 1) Cria a pasta onde os segmentos de áudio brutos serão gravados
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # 2) Cria a pasta onde o HLS será gerado (hls/{channel}/{lang}/index.m3u8 + .ts)
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # 3) Dispara o processo de captura (streamlink → ffmpeg → .wav) via multiprocessing
    p_capture = Process(target=start_capture, args=(channel, audio_dir), daemon=True)
    p_capture.start()
    logger.info(f"[backend] Processo de captura iniciado com PID {p_capture.pid}.")

    # 4) Dispara o processo do worker (Whisper → DeepL/Coqui → HLS) via multiprocessing
    #    Atenção: worker_loop recebe exatamente 2 parâmetros: audio_dir e lang
    p_worker = Process(target=worker_loop, args=(audio_dir, lang), daemon=True)
    p_worker.start()
    logger.info(f"[backend] Processo de worker iniciado com PID {p_worker.pid}.")

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_pipeline(channel: str):
    """
    Endpoint placeholder para parar captura e processamento de um canal.
    (Implementar sinalização para encerrar correctamente os subprocessos, se necessário.)
    """
    # Por enquanto, apenas retorna que foi "parado"
    logger.info(f"Parando pipeline para canal=\'{channel}\'.")
    return {"status": "parado", "channel": channel}

# --- Montagem dos Arquivos Estáticos (DEVE VIR DEPOIS DAS ROTAS DA API) ---

# Monta o diretório 'hls' para servir arquivos HLS (.m3u8 e .ts)
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# Monta o diretório 'frontend/dist' para servir o React na raiz
# Esta deve ser a ÚLTIMA montagem para não sobrescrever as rotas da API
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

