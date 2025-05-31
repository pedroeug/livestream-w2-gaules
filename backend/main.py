# livestream-w2-gaules/backend/main.py

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# Importa o módulo para garantir que o modelo Whisper esteja baixado
from backend.download_models import download_all_models

# Importa a função que inicia a captura de áudio da Twitch
from capture.recorder import start_capture

# Importa o loop de worker que faz transcrição (Whisper), tradução (DeepL),
# síntese de voz (ElevenLabs) e montagem de HLS
from pipeline.worker import worker_loop

app = FastAPI()

# Permitir CORS para qualquer origem (ajuste conforme sua necessidade)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Antes de qualquer coisa, baixa/verifica o modelo Whisper
download_all_models()


@app.get("/")
async def root():
    """
    Endpoint raiz apenas para verificar se o backend está funcionando.
    """
    return {"message": "LiveDub backend está rodando"}


@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str, background_tasks: BackgroundTasks):
    """
    Inicia o processo de captura e processamento em segundo plano.

    Parâmetros:
    - channel: nome do canal Twitch (ex: "gaules")
    - lang: código do idioma de saída para tradução/síntese (ex: "en", "pt", "es")

    O processamento envolve:
    1) Capturar áudio em segmentos de 10 segundos.
    2) Transcrever cada segmento com Whisper.
    3) Traduzir com DeepL.
    4) Sintetizar voz com ElevenLabs.
    5) Montar HLS com FFmpeg.

    Retorna imediatamente um objeto informando que o processo foi disparado.
    """
    # Pasta onde serão salvos os segmentos de áudio brutos
    output_dir = os.path.join("audio_segments", channel)
    os.makedirs(output_dir, exist_ok=True)

    # Adiciona ao pool de tarefas em background a captura de áudio
    background_tasks.add_task(start_capture, channel, output_dir)

    # Adiciona ao pool de tarefas em background o worker que processa cada segmento
    background_tasks.add_task(worker_loop, output_dir, lang)

    return {"status": "iniciado", "channel": channel, "lang": lang}


@app.post("/stop/{channel}")
async def stop_stream(channel: str):
    """
    Endpoint para interromper a captura/processamento de um canal.
    Atualmente, essa função serve de placeholder, pois o processo de captura
    é disparado em um subprocesso independente. Para interromper, seria necessário
    monitorar e matar o processo Popen dentro de capture.recorder, ou usar um flag
    de controle. Aqui retornamos apenas um status genérico.
    """
    # Em projetos futuros, aqui poderíamos sinalizar para o recorder/worker parar
    return {"status": "parado", "channel": channel}


@app.get("/health")
async def health_check():
    """
    Endpoint para checagem de integridade (health check).
    """
    return {"status": "ok"}
