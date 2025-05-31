# livestream-w2-gaules/capture/recorder.py

import os
import subprocess
import shlex

def start_capture(channel_name: str, output_dir: str):
    """
    Inicia o ffmpeg para capturar áudio do canal Twitch usando streamlink,
    segmentando em partes de 10 segundos e salvando em WAV.

    A pipe do streamlink fornece o fluxo HLS da Twitch diretamente para o ffmpeg.
    """

    os.makedirs(output_dir, exist_ok=True)

    # Monta o comando para streamlink → ffmpeg
    cmd_str = (
        f'streamlink --twitch-disable-hosting twitch.tv/{channel_name} best '
        f'| ffmpeg -hide_banner -loglevel error -i - -vn '
        f'-acodec pcm_s16le -ar 48000 -ac 2 '
        f'-f segment -segment_time 10 -reset_timestamps 1 '
        f'{output_dir}/segment_%03d.wav'
    )
    print(f"[recorder] Comando completo para captura: {cmd_str}")

    log_path = os.path.join(output_dir, "ffmpeg_capture.log")
    print(f"[recorder] Salvando logs do ffmpeg em: {log_path}")

    # Executa o ffmpeg via subprocess, redirecionando stdout e stderr para o arquivo de log
    with open(log_path, "a") as log_file:
        process = subprocess.Popen(
            shlex.split(cmd_str),
            stdout=log_file,
            stderr=log_file
        )
    print(f"[recorder] FFmpeg iniciado com PID {process.pid}. Gravando em {output_dir}/segment_*.wav")
