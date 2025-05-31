# livestream-w2-gaules/pipeline/worker_debug.py
# Versão de debug do worker com logs detalhados em cada etapa

import os
import time
import sys
import traceback
import whisper
from deep_translator import DeeplTranslator
import subprocess
import logging
import shutil
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de logging mais detalhada
logger = logging.getLogger("worker_debug")
logger.setLevel(logging.DEBUG)

# Handler para console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Handler para arquivo
file_handler = logging.FileHandler("worker_debug_detailed.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def process_single_segment(wav_path, lang):
    """
    Processa um único segmento de áudio para debug.
    """
    try:
        logger.debug(f"[DEBUG] Iniciando processamento do segmento: {wav_path}")
        
        # 1) Transcrição com Whisper
        logger.debug(f"[DEBUG] Carregando modelo Whisper...")
        model = whisper.load_model("base")
        logger.debug(f"[DEBUG] Modelo Whisper carregado com sucesso")
        
        logger.debug(f"[DEBUG] Transcrevendo {wav_path} com idioma forçado para português...")
        result = model.transcribe(wav_path, language="pt")
        text = result["text"].strip()
        logger.debug(f"[DEBUG] Transcrição concluída: {text}")

        # 2) Tradução com DeepL
        logger.debug(f"[DEBUG] Preparando tradução para {lang}...")
        try:
            # Ler a chave da API do ambiente
            deepl_api_key = os.getenv("DEEPL_API_KEY")
            logger.debug(f"[DEBUG] Chave DeepL encontrada: {deepl_api_key[:5]}...")
            
            if not deepl_api_key:
                raise ValueError("DEEPL_API_KEY não encontrada no ambiente.")
            
            # Passar api_key e use_free_api explicitamente
            logger.debug(f"[DEBUG] Inicializando DeeplTranslator...")
            translator = DeeplTranslator(api_key=deepl_api_key, source="auto", target=lang, use_free_api=True)
            
            logger.debug(f"[DEBUG] Traduzindo texto...")
            translated = translator.translate(text)
            logger.debug(f"[DEBUG] Tradução concluída: {translated}")
        except Exception as deepl_error:
            logger.error(f"[DEBUG] Erro na API DeepL: {deepl_error}")
            logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
            logger.debug(f"[DEBUG] Usando texto original como fallback")
            translated = text

        # 3) Pular síntese de voz e usar o áudio original
        logger.debug(f"[DEBUG] Pulando síntese de voz e usando áudio original...")
        
        # Converter WAV original para MP3
        dubbed_mp3 = wav_path.replace(".wav", "_debug.mp3")
        logger.debug(f"[DEBUG] Convertendo WAV para MP3: {wav_path} -> {dubbed_mp3}")
        
        try:
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", wav_path, 
                "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", 
                dubbed_mp3
            ]
            logger.debug(f"[DEBUG] Executando comando ffmpeg: {' '.join(ffmpeg_cmd)}")
            
            process = subprocess.run(
                ffmpeg_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.debug(f"[DEBUG] Saída do ffmpeg: {process.stdout.decode('utf-8', errors='ignore')}")
            logger.debug(f"[DEBUG] Erro do ffmpeg: {process.stderr.decode('utf-8', errors='ignore')}")
            
            if os.path.exists(dubbed_mp3):
                logger.debug(f"[DEBUG] Arquivo MP3 gerado com sucesso: {dubbed_mp3}")
                logger.debug(f"[DEBUG] Tamanho do arquivo: {os.path.getsize(dubbed_mp3)} bytes")
            else:
                logger.error(f"[DEBUG] Arquivo MP3 não foi gerado!")
        except Exception as ffmpeg_error:
            logger.error(f"[DEBUG] Erro ao converter para MP3: {ffmpeg_error}")
            logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return False

        # 4) Criar diretório HLS
        channel = os.path.basename(os.path.dirname(wav_path))
        hls_dir = os.path.join("hls", channel, lang)
        logger.debug(f"[DEBUG] Criando diretório HLS: {hls_dir}")
        os.makedirs(hls_dir, exist_ok=True)

        # 5) Empacotar em HLS via ffmpeg
        ts_pattern = os.path.join(hls_dir, "debug_%03d.ts")
        output_index = os.path.join(hls_dir, "debug.m3u8")

        logger.debug(f"[DEBUG] Convertendo {dubbed_mp3} para HLS em {output_index} ...")
        try:
            ffmpeg_hls_cmd = [
                "ffmpeg", "-y",
                "-i", dubbed_mp3,
                "-c:a", "aac", "-b:a", "128k",
                "-vn",
                "-hls_time", "10",
                "-hls_playlist_type", "event",
                "-hls_segment_filename", ts_pattern,
                output_index
            ]
            logger.debug(f"[DEBUG] Executando comando ffmpeg HLS: {' '.join(ffmpeg_hls_cmd)}")
            
            process = subprocess.run(
                ffmpeg_hls_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.debug(f"[DEBUG] Saída do ffmpeg HLS: {process.stdout.decode('utf-8', errors='ignore')}")
            logger.debug(f"[DEBUG] Erro do ffmpeg HLS: {process.stderr.decode('utf-8', errors='ignore')}")
            
            if os.path.exists(output_index):
                logger.debug(f"[DEBUG] Arquivo HLS gerado com sucesso: {output_index}")
                logger.debug(f"[DEBUG] Conteúdo do diretório HLS: {os.listdir(hls_dir)}")
                return True
            else:
                logger.error(f"[DEBUG] Arquivo HLS não foi gerado!")
                return False
        except Exception as hls_error:
            logger.error(f"[DEBUG] Erro ao gerar HLS: {hls_error}")
            logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return False
            
    except Exception as e:
        logger.error(f"[DEBUG] Erro geral no processamento: {e}")
        logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Verificar se foi passado um arquivo WAV como argumento
    if len(sys.argv) < 2:
        logger.error("Uso: python worker_debug.py <caminho_para_wav>")
        sys.exit(1)
    
    wav_path = sys.argv[1]
    lang = "en" if len(sys.argv) < 3 else sys.argv[2]
    
    if not os.path.exists(wav_path):
        logger.error(f"Arquivo não encontrado: {wav_path}")
        sys.exit(1)
    
    logger.debug(f"[DEBUG] Iniciando debug com arquivo: {wav_path}, idioma: {lang}")
    
    success = process_single_segment(wav_path, lang)
    
    if success:
        logger.debug("[DEBUG] Processamento concluído com sucesso!")
    else:
        logger.error("[DEBUG] Processamento falhou!")
