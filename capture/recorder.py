# livestream-w2-gaules/capture/recorder.py

import os
import subprocess
import shlex
import logging
import threading

logger = logging.getLogger("recorder")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_stderr(pipe, log_func):
    try:
        for line in iter(pipe.readline, b''):
            log_func(line.decode().strip())
    finally:
        pipe.close()

def start_capture(channel_name: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Diretório de saída garantido: {output_dir}")

    streamlink_cmd = [
        "streamlink",
        "--twitch-disable-hosting",
        f"twitch.tv/{channel_name}",
        "best",
        "-O"
    ]

    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error", # Log only errors from ffmpeg
        "-i", "-", # Input from stdin
        "-vn", # No video
        "-acodec", "pcm_s16le",
        "-ar", "48000",
        "-ac", "2",
        "-f", "segment",
        "-segment_time", "10",
        "-reset_timestamps", "1",
        f"{output_dir}/segment_%03d.wav"
    ]

    logger.info(f"[recorder] Iniciando streamlink: {' '.join(streamlink_cmd)}")
    logger.info(f"[recorder] Iniciando ffmpeg: {' '.join(ffmpeg_cmd)}")

    log_path = os.path.join(output_dir, "ffmpeg_capture.log")
    logger.info(f"[recorder] Salvando logs do ffmpeg em: {log_path}")

    try:
        # Start streamlink process
        streamlink_proc = subprocess.Popen(
            streamlink_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"[recorder] Streamlink iniciado com PID {streamlink_proc.pid}")

        # Start ffmpeg process, taking input from streamlink's stdout
        with open(log_path, "ab") as log_file: # Append binary mode
            ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=streamlink_proc.stdout,
                stdout=log_file, # Redirect ffmpeg stdout to log
                stderr=log_file  # Redirect ffmpeg stderr to log
            )
            logger.info(f"[recorder] FFmpeg iniciado com PID {ffmpeg_proc.pid}. Gravando em {output_dir}/segment_*.wav")

        # Allow streamlink_proc.stdout to be closed by ffmpeg_proc when done
        streamlink_proc.stdout.close()

        # Log streamlink stderr in a separate thread to avoid blocking
        stderr_thread = threading.Thread(target=log_stderr, args=(streamlink_proc.stderr, logger.error))
        stderr_thread.start()

        # Wait for ffmpeg to finish (it will finish when streamlink closes stdout or errors)
        ffmpeg_exit_code = ffmpeg_proc.wait()
        logger.info(f"[recorder] FFmpeg (PID {ffmpeg_proc.pid}) finalizado com código: {ffmpeg_exit_code}")

        # Wait for streamlink to finish and get its exit code
        streamlink_exit_code = streamlink_proc.wait()
        logger.info(f"[recorder] Streamlink (PID {streamlink_proc.pid}) finalizado com código: {streamlink_exit_code}")

        # Ensure stderr logging thread finishes
        stderr_thread.join()

        if streamlink_exit_code != 0:
            logger.error(f"Streamlink falhou com código {streamlink_exit_code}. Verifique os logs de erro acima.")
        if ffmpeg_exit_code != 0:
            logger.error(f"FFmpeg falhou com código {ffmpeg_exit_code}. Verifique {log_path}")

    except FileNotFoundError as e:
        logger.error(f"Erro: Comando não encontrado - {e}. Verifique se streamlink e ffmpeg estão instalados e no PATH correto.")
    except Exception as e:
        logger.error(f"Erro inesperado ao iniciar a captura: {e}")


