# livestream-w2-gaules/capture/recorder.py

import os
import subprocess
import logging
import time
import threading
from queue import Queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recorder")


def start_capture(channel_name: str, output_dir: str, log_queue: Queue | None = None):
    """
    Inicia o FFmpeg para capturar o áudio do canal da Twitch, gerando arquivos
    WAV de 10 segundos. Se `log_queue` for fornecida, as mensagens de log serão
    encaminhadas para essa fila.
    """
    os.makedirs(output_dir, exist_ok=True)
    cmd_str = (
        f"streamlink --twitch-disable-hosting twitch.tv/{channel_name} best -O "
        f"| ffmpeg -hide_banner -loglevel error -i - -vn "
        f"-acodec pcm_s16le -ar 48000 -ac 2 "
        f"-f segment -segment_time 10 -reset_timestamps 1 "
        f"{output_dir}/segment_%03d.wav"
    )
    logger.info(f"[recorder] Comando completo para captura: {cmd_str}")

    log_path = os.path.join(output_dir, "ffmpeg_capture.log")
    logger.info(f"[recorder] Salvando logs do ffmpeg em: {log_path}")

    if log_queue is not None:
        class QueueHandler(logging.Handler):
            def emit(self, record):
                log_queue.put(self.format(record))

        qh = QueueHandler()
        qh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(qh)

    with open(log_path, "a") as log_file:
        process = subprocess.Popen(
            cmd_str,
            shell=True,
            stdout=log_file,
            stderr=log_file
        )

    logger.info(
        f"[recorder] FFmpeg iniciado com PID {process.pid}. Gravando em {output_dir}/segment_*.wav"
    )

    def verify_start() -> None:
        time.sleep(5)
        if not any(f.endswith('.wav') for f in os.listdir(output_dir)):
            warn_msg = (
                "[recorder] AVISO: nenhum segmento foi criado em 5s. Verifique streamlink/ffmpeg."
            )
            logger.warning(warn_msg)
            if log_queue:
                log_queue.put(warn_msg)

    threading.Thread(target=verify_start, daemon=True).start()

    return process
