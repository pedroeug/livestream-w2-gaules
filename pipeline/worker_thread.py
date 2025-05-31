# livestream-w2-gaules/pipeline/worker_thread.py

import os
import time
import threading
import traceback
import logging
from pipeline.worker import worker_loop

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("worker_thread.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("worker_thread")

def worker_wrapper(audio_dir: str, lang: str):
    """
    Wrapper para capturar exceções no worker_loop
    """
    try:
        logger.info(f"Iniciando worker_loop para {audio_dir} e idioma {lang}")
        worker_loop(audio_dir, lang)
    except Exception as e:
        logger.error(f"ERRO CRÍTICO no worker_loop: {e}")
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        # Tentar reiniciar o worker após um erro crítico
        logger.info("Tentando reiniciar o worker após erro crítico...")
        time.sleep(5)  # Aguardar um pouco antes de reiniciar
        try:
            worker_loop(audio_dir, lang)
        except Exception as e2:
            logger.error(f"Falha ao reiniciar worker após erro: {e2}")

def start_worker_thread(audio_dir: str, lang: str):
    """
    Inicia o worker_loop em uma thread separada para evitar
    bloqueio do event loop do FastAPI.
    """
    # Garantir que o diretório de áudio existe
    os.makedirs(audio_dir, exist_ok=True)
    
    # Garantir que o diretório HLS existe
    channel = os.path.basename(os.path.abspath(audio_dir))
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)
    
    # Criar diretório para arquivos processados
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    
    # Iniciar o worker em uma thread separada
    worker_thread = threading.Thread(
        target=worker_wrapper,
        args=(audio_dir, lang),
        daemon=True
    )
    worker_thread.start()
    logger.info(f"Worker iniciado em thread separada para {audio_dir} e idioma {lang}")
    
    # Verificar se a thread está realmente rodando
    time.sleep(1)
    if worker_thread.is_alive():
        logger.info("Thread do worker está rodando corretamente")
    else:
        logger.error("ERRO: Thread do worker não está rodando!")
    
    return worker_thread
