# livestream-w2-gaules/capture/recorder.py

import os
import subprocess

def start_capture(channel_name: str, output_dir: str):
    """
    Inicia a captura de áudio do canal Twitch especificado e salva em segmentos de 10 segundos.
    Usa o ffmpeg para criar arquivos WAV (PCM s16le, 48 kHz, estéreo) em output_dir.

    Parâmetros:
    - channel_name: nome do canal Twitch (por exemplo, "gaules")
    - output_dir: pasta onde os segmentos de áudio serão salvos (por exemplo, "./audio_segments")
    """

    # Garante que a pasta de saída exista
    os.makedirs(output_dir, exist_ok=True)

    # Comando ffmpeg para capturar áudio do stream da Twitch e segmentar em arquivos de 10 segundos
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", f"https://www.twitch.tv/{channel_name}",
        "-vn",                             # skip video
        "-acodec", "pcm_s16le",            # áudio em PCM 16 bits
        "-ar", "48000",                    # sample rate 48 kHz
        "-ac", "2",                        # estéreo
        "-f", "segment",                   # segmenta o stream
        "-segment_time", "10",             # duração de cada segmento: 10 segundos
        "-reset_timestamps", "1",          # reseta timestamps a cada segmento
        f"{output_dir}/segment_%03d.wav"   # nome dos arquivos gerados: segment_000.wav, segment_001.wav, etc.
    ]

    # Inicia processo separado, sem bloquear
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
