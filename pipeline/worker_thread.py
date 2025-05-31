# livestream-w2-gaules/pipeline/worker_thread.py

import os
import time
import threading
import whisper
from deep_translator import DeeplTranslator
import requests
import subprocess
from pipeline.worker import worker_loop

def start_worker_thread(audio_dir: str, lang: str):
    """
    Inicia o worker_loop em uma thread separada para evitar
    bloqueio do event loop do FastAPI.
    """
    worker_thread = threading.Thread(
        target=worker_loop,
        args=(audio_dir, lang),
        daemon=True
    )
    worker_thread.start()
    print(f"[worker_thread] Worker iniciado em thread separada para {audio_dir} e idioma {lang}")
    return worker_thread
