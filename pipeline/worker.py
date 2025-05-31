# livestream-w2-gaules/pipeline/worker_simplified.py
# Versão simplificada do worker que pula a etapa de TTS e usa áudio original

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess
import logging
import shutil
from dotenv import load_dotenv  # Adicionado para carregar variáveis de ambiente

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

logger = logging.getLogger("worker_simplified")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Pula a síntese de voz e usa o áudio original.
      5. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # 1) Carrega o modelo Whisper
    logger.info("[worker] Carregando modelo Whisper...")
    model = whisper.load_model("base")
    logger.info("[worker] Modelo Whisper carregado com sucesso!")

    processed = set()

    # 2) Garante diretório de `processed/` para cada canal
    channel = os.path.basename(audio_dir)
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # 3) Cria um arquivo inicial de concatenação MP3 vazio usando um áudio nulo
    concat_mp3 = os.path.join(processed_dir, "concat.mp3")
    if not os.path.exists(concat_mp3):
        # Geramos um MP3 curto de áudio em silêncio para iniciar
        logger.info(f"[worker] Criando arquivo inicial de concatenação: {concat_mp3}")
        temp_silent_wav = os.path.join(processed_dir, "silent.wav")
        # gera 1 segundo de silêncio em WAV
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                "-t", "1",
                temp_silent_wav
            ], check=True)
            # converte para MP3
            subprocess.run([
                "ffmpeg", "-y",
                "-i", temp_silent_wav,
                "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1",
                concat_mp3
            ], check=True)
            if os.path.exists(temp_silent_wav):
                os.remove(temp_silent_wav)
            logger.info(f"[worker] Arquivo inicial de concat.mp3 criado em {concat_mp3}")
        except Exception as e:
            logger.error(f"[worker] Erro ao criar arquivo inicial: {e}")

    logger.info("[worker] Iniciando loop de processamento de segmentos...")
    while True:
        # Percorre os arquivos WAV novos não processados
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"[worker] Processando segmento: {wav_path}")

            try:
                # 1) Transcrição com Whisper
                logger.info(f"[worker] Transcrevendo {wav_path} com idioma forçado para português...")
                result = model.transcribe(wav_path, language="pt")
                text = result["text"].strip()
                logger.info(f"[worker] Transcrição: {text}")

                # 2) Tradução com DeepL
                target_lang = lang # Usar 'en', 'pt', 'es' diretamente
                logger.info(f"[worker] Traduzindo para {target_lang} ...")
                try:
                    # Ler a chave da API do ambiente
                    deepl_api_key = os.getenv("DEEPL_API_KEY")
                    logger.info(f"[worker] Chave DeepL encontrada: {deepl_api_key[:5]}...")
                    
                    if not deepl_api_key:
                        raise ValueError("DEEPL_API_KEY não encontrada no ambiente.")
                    
                    # Passar api_key e use_free_api explicitamente
                    translator = DeeplTranslator(api_key=deepl_api_key, source="auto", target=target_lang, use_free_api=True)
                    translated = translator.translate(text)
                    logger.info(f"[worker] Tradução: {translated}")
                except Exception as deepl_error:
                    logger.error(f"[worker] Erro na API DeepL: {deepl_error}. Usando texto original para processamento.")
                    # Fallback: Usar o texto original se a tradução falhar
                    translated = text

                # 3) MODIFICAÇÃO: Pular síntese de voz e usar o áudio original
                logger.info(f"[worker] Pulando síntese de voz e usando áudio original...")
                
                # Converter WAV original para MP3
                dubbed_mp3 = wav_path.replace(".wav", ".mp3")
                logger.info(f"[worker] Convertendo WAV para MP3: {wav_path} -> {dubbed_mp3}")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", wav_path, "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", dubbed_mp3],
                    check=True
                )
                logger.info(f"[worker] Arquivo convertido para MP3: {dubbed_mp3}")

                # 4) Adiciona esse MP3 ao arquivo contínuo de concatenação
                logger.info(f"[worker] Adicionando segmento ao arquivo contínuo: {concat_mp3}")
                temp_concat = concat_mp3 + ".temp"
                
                # Verificar se o arquivo concat_mp3 existe
                if not os.path.exists(concat_mp3):
                    logger.warning(f"[worker] Arquivo de concatenação não existe, copiando o primeiro MP3 como base")
                    shutil.copy(dubbed_mp3, concat_mp3)
                else:
                    # Usar o método de concatenação do ffmpeg
                    concat_input = f"concat:{concat_mp3}|{dubbed_mp3}"
                    try:
                        subprocess.run(
                            ["ffmpeg", "-y", "-i", concat_input, "-acodec", "copy", temp_concat],
                            check=True
                        )
                        # Substitui o concat antigo pelo novo
                        os.replace(temp_concat, concat_mp3)
                        logger.info(f"[worker] Segmento adicionado com sucesso ao arquivo contínuo")
                    except Exception as concat_error:
                        logger.error(f"[worker] Erro na concatenação: {concat_error}")
                        # Fallback: Se falhar, apenas use o último MP3
                        shutil.copy(dubbed_mp3, concat_mp3)
                        logger.info(f"[worker] Fallback: Usando apenas o último MP3 como arquivo contínuo")

                # 5) Empacotar em HLS via ffmpeg
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                logger.info(f"[worker] Convertendo {concat_mp3} para HLS em {output_index} ...")
                try:
                    ffmpeg_cmd = [
                        "ffmpeg", "-y",
                        "-i", concat_mp3,
                        "-c:a", "aac", "-b:a", "128k",
                        "-vn",
                        "-hls_time", "10",
                        "-hls_playlist_type", "event",
                        "-hls_segment_filename", ts_pattern,
                        output_index
                    ]
                    subprocess.run(ffmpeg_cmd, check=True)
                    logger.info(f"[worker] HLS gerado com sucesso em {output_index}")
                except Exception as hls_error:
                    logger.error(f"[worker] Erro ao gerar HLS: {hls_error}")

                processed.add(filename)
                logger.info(f"[worker] Segmento {filename} processado com sucesso")

            except Exception as e:
                logger.error(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
