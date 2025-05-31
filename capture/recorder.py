# livestream-w2-gaules/capture/recorder.py

import os
import subprocess
import shlex

def start_capture(channel_name: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # Constrói o comando como string para facilitar o debug
    cmd_str = (
        f'ffmpeg -hide_banner -loglevel error '
        f'-i https://www.twitch.tv/{channel_name} '
        f'-vn -acodec pcm_s16le -ar 48000 -ac 2 '
        f'-f segment -segment_time 10 -reset_timestamps 1 '
        f'{output_dir}/segment_%03d.wav'
    )
    print(f"[recorder] Comando FFmpeg: {cmd_str}")

    # Executa o ffmpeg em Popen; redireciona stdout/stderr para arquivos de log
    log_path = os.path.join(output_dir, "ffmpeg_capture.log")
    with open(log_path, "a") as log_file:
        process = subprocess.Popen(
            shlex.split(cmd_str),
            stdout=log_file,
            stderr=log_file
        )
    print(f"[recorder] FFmpeg PID {process.pid} iniciou. Logs em: {log_path}")
