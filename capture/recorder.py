# livestream-w2-gaules/capture/recorder.py

import os
import subprocess
import shlex
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recorder")


def start_capture(channel_name: str, output_dir: str):
    """
    Inicia o ffmpeg para capturar áudio do canal Twitch, segmentando em .wav de 10s.
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

    with open(log_path, "a") as log_file:
        process = subprocess.Popen(
            shlex.split(cmd_str),
            stdout=log_file,
            stderr=log_file
        )
    logger.info(f"[recorder] FFmpeg iniciado com PID {process.pid}. Gravando em {output_dir}/segment_*.wav")
    return process
