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

    log_path = os.path.join(output_dir, "ffmpeg_capture.log")
    logger.info(f"Salvando logs do ffmpeg em: {log_path}")

    # Método direto usando shell=True e o comando completo com pipe
    # Este método funciona conforme verificado no teste manual
    cmd_str = (
        f'streamlink --twitch-disable-hosting twitch.tv/{channel_name} best -O | '
        f'ffmpeg -hide_banner -loglevel error -i - -vn '
        f'-acodec pcm_s16le -ar 48000 -ac 2 '
        f'-f segment -segment_time 10 -reset_timestamps 1 '
        f'{output_dir}/segment_%03d.wav'
    )
    logger.info(f"Comando completo para captura: {cmd_str}")

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
                # Método alternativo usando script shell temporário
                script_path = os.path.join(output_dir, "capture_script.sh")
                with open(script_path, "w") as script_file:
                    script_file.write("#!/bin/bash\n")
                    script_file.write(f"streamlink --twitch-disable-hosting twitch.tv/{channel_name} best -O | \\\n")
                    script_file.write(f"ffmpeg -hide_banner -loglevel error -i - -vn \\\n")
                    script_file.write(f"-acodec pcm_s16le -ar 48000 -ac 2 \\\n")
                    script_file.write(f"-f segment -segment_time 10 -reset_timestamps 1 \\\n")
                    script_file.write(f"{output_dir}/segment_%03d.wav\n")
                
                # Tornar o script executável
                os.chmod(script_path, 0o755)
                
                # Executar o script
                with open(log_path, "a") as log_file:
                    alt_process = subprocess.Popen(
                        script_path,
                        shell=True,
                        stdout=log_file,
                        stderr=log_file
                    )
                
                logger.info(f"Método alternativo iniciado via script. PID: {alt_process.pid}")
                return alt_process
            except Exception as e:
                logger.error(f"Falha no método alternativo via script: {e}")
        
        return process
    except Exception as e:
        logger.error(f"Erro ao iniciar processo de captura: {e}")
        return None
