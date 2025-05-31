# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importa o download de modelos Whisper (arquivo download_models.py está em backend/)
from download_models import download_all_models

# Importa a captura de áudio da Twitch (pasta capture/recorder.py no nível da raiz)
from capture.recorder import start_capture

# Importa o worker que faz transcrição, tradução, síntese e gera HLS (pasta pipeline/worker.py no nível da raiz)
from pipeline.worker import worker_loop

app = FastAPI()

# Configura CORS para permitir qualquer origem (ajuste se necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1) Baixa/verifica o modelo Whisper ao iniciar ---
download_all_models()

# --- 2) Garante que a pasta 'hls' exista ― e monta como StaticFiles ---
os.makedirs("hls", exist_ok=True)
# Monta a pasta local "hls/" na rota "/hls"
app.mount("/hls", StaticFiles(directory="hls"), name="hls")


# --- 3) Monta o build gerado pelo React como StaticFiles na raiz "/" ---
# A pasta "frontend/dist" contém index.html, o JavaScript empacotado, assets, etc.
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


# --- 4) Endpoints da API ---
@app.get("/health")
async def health_check():
    """
    Health check para verificar se o backend está funcionando.
    """
    return {"status": "ok"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia captura e processamento em segundo plano:
      - start_capture grava áudio da Twitch em segmentos de 10s dentro de audio_segments/{channel}/
      - worker_loop transcreve, traduz, sintetiza e gera HLS em hls/{channel}/{lang}/
    """

    # 4.1. Cria (se não existir) a pasta onde os .wav brutos serão armazenados:
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    # 4.2. Cria (se não existir) a pasta onde o HLS será gerado:
    #       hls/{channel}/{lang}/index.m3u8  e   hls/{channel}/{lang}/000.ts, 001.ts, …
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # 4.3. Dispara as tarefas em background ― sem bloquear a resposta HTTP
    #       a) primeira tarefa: captura de áudio contínua (streamlink → ffmpeg → .wav)
    background_tasks.add_task(start_capture, channel, audio_dir)
    #       b) segunda tarefa: worker processa cada .wav, gera transcrição, tradução, TTS e segmentos HLS
    background_tasks.add_task(worker_loop, audio_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    (Opcional) Placeholder para encerrar captura e processamento de um canal.
    Por ora, apenas responde que “parou”, mas você pode implementar lógica
    para sinalizar ao start_capture e ao worker_loop que parem suas threads.
    """
    return {"status": "parado", "channel": channel}
