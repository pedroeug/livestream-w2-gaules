# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importa o download de modelos Whisper (arquivo: backend/download_models.py)
from backend.download_models import download_all_models

# Importa a função que inicia a captura via streamlink+ffmpeg (arquivo: capture/recorder.py)
from capture.recorder import start_capture

# Importa o worker que faz transcrição, tradução, síntese e empacota em HLS
# (arquivo: pipeline/worker.py)
from pipeline.worker import worker_loop

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
    # 3.1) Cria pasta para armazenar segmentos de áudio brutos
    audio_dir = os.path.join("audio_segments", channel)
    try:
        os.makedirs(audio_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao criar pasta audio_segments/{channel}: {e}")

    # 3.2) Cria pasta onde serão gerados os arquivos HLS: hls/{channel}/{lang}/
    hls_dir = os.path.join("hls", channel, lang)
    try:
        os.makedirs(hls_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao criar pasta hls/{channel}/{lang}: {e}")

    # 3.3) Dispara as duas tarefas em background:
    #      1) start_capture(channel, audio_dir) –> gera segment_XXX.wav em audio_segments/channel/
    #      2) worker_loop(audio_dir, lang) –> monitora audio_segments/channel/ e gera HLS em hls/channel/lang/
    background_tasks.add_task(start_capture, channel, audio_dir)
    background_tasks.add_task(worker_loop, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


# -------------------------------------------------------------
# 4) Rota para parar captura/processing (placeholder)
# -------------------------------------------------------------
@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Placeholder para parar captura e processamento de um canal.
    (Ainda não implementado adequadamente; apenas retorna status.)
    """
    return {"status": "parado", "channel": channel}


# -------------------------------------------------------------
# 5) Na inicialização, baixa/verifica o modelo Whisper e garante pasta HLS
# -------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    # 5.1) Baixa/verifica o modelo Whisper (podendo demorar alguns segundos)
    print("[startup] Baixando/verificando modelos Whisper...")
    download_all_models()
    print("[startup] Modelos Whisper prontos.")

    # 5.2) Garante que exista a pasta "hls" na raiz (para servir os arquivos HLS)
    try:
        os.makedirs("hls", exist_ok=True)
    except Exception as e:
        print(f"[startup] Não foi possível criar pasta 'hls': {e}")



# -------------------------------------------------------------
# 6) Montagem dos diretórios como “arquivos estáticos”
#
#    IMPORTANTE: crie as rotas “dinâmicas” ANTES destes mounts.
# -------------------------------------------------------------
# 6.1) Monta a pasta “hls” na rota “/hls” para servir .m3u8 e .ts
app.mount("/hls", StaticFiles(directory="hls", html=False), name="hls")

# 6.2) Monta a pasta “frontend/dist” na raiz para servir o React
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
