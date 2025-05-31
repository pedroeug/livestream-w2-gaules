# livestream-w2-gaules/capture/recorder.py

import os
import subprocess
import shlex
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("recorder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("recorder")

def start_capture(channel_name: str, output_dir: str):
    """
    Inicia o ffmpeg para capturar áudio do canal Twitch usando streamlink,
    segmentando em partes de 10 segundos e salvando em WAV.

    A pipe do streamlink fornece o fluxo HLS da Twitch diretamente para o ffmpeg.
    """

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Diretório de saída garantido: {output_dir}")

    # Monta o comando para streamlink → ffmpeg
    cmd_str = (
        f'streamlink --twitch-disable-hosting twitch.tv/{channel_name} best '
        f'| ffmpeg -hide_banner -loglevel error -i - -vn '
        f'-acodec pcm_s16le -ar 48000 -ac 2 '
        f'-f segment -segment_time 10 -reset_timestamps 1 '
        f'{output_dir}/segment_%03d.wav'
    )
    logger.info(f"Comando completo para captura: {cmd_str}")

    log_path = os.path.join(output_dir, "ffmpeg_capture.log")
    logger.info(f"Salvando logs do ffmpeg em: {log_path}")

    # Executa o comando via subprocess com shell=True para permitir o uso de pipe
    try:
        with open(log_path, "a") as log_file:
            process = subprocess.Popen(
                cmd_str,
                shell=True,
                stdout=log_file,
                stderr=log_file
            )
        logger.info(f"FFmpeg iniciado com PID {process.pid}. Gravando em {output_dir}/segment_*.wav")
        
        # Verificar se o processo está realmente rodando
        if process.poll() is None:
            logger.info("Processo de captura está rodando corretamente")
        else:
            logger.error(f"ERRO: Processo de captura falhou com código {process.returncode}")
            # Tentar novamente com uma abordagem alternativa
            logger.info("Tentando método alternativo de captura...")
            try:
                # Método alternativo usando dois comandos separados
                streamlink_cmd = f'streamlink --twitch-disable-hosting twitch.tv/{channel_name} best -O'
                ffmpeg_cmd = (
                    f'ffmpeg -hide_banner -loglevel error -i pipe:0 -vn '
                    f'-acodec pcm_s16le -ar 48000 -ac 2 '
                    f'-f segment -segment_time 10 -reset_timestamps 1 '
                    f'{output_dir}/segment_%03d.wav'
                )
                
                # Executar streamlink e capturar sua saída
                streamlink_process = subprocess.Popen(
                    streamlink_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=log_file
                )
                
                # Alimentar a saída do streamlink para o ffmpeg
                ffmpeg_process = subprocess.Popen(
                    ffmpeg_cmd,
                    shell=True,
                    stdin=streamlink_process.stdout,
                    stdout=log_file,
                    stderr=log_file
                )
                
                # Permitir que streamlink_process seja fechado quando ffmpeg_process terminar
                streamlink_process.stdout.close()
                
                logger.info(f"Método alternativo iniciado. FFmpeg PID: {ffmpeg_process.pid}")
            except Exception as e:
                logger.error(f"Falha no método alternativo: {e}")
        
        return process
    except Exception as e:
        logger.error(f"Erro ao iniciar processo de captura: {e}")
        return None
