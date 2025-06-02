# livestream-w2-gaules/pipeline/worker.py

import os
import time
import shutil
import logging
import requests
import subprocess

import whisper
from deep_translator import DeeplTranslator

logger = logging.getLogger("worker")
logger.setLevel(logging.INFO)
# Se quiser que o log apareça no console:
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# (1) Carrega credenciais do Speechify
SPEECHIFY_API_KEY = os.getenv("SPEECHIFY_API_KEY", "").strip()
VOICE_ID = "3af44bf3-439e-4e9d-a6ff-4870d437ef7a"  # ID de voz que você informou
# Endpoint básico (confirme na sua documentação Speechify; este é um exemplo genérico)
SPEECHIFY_TTS_ENDPOINT = "https://api.speechify.com/v1/tts"


def text_to_speech_with_speechify(text: str, output_wav_path: str, language: str) -> bool:
    """
    Envia o `text` ao Speechify via HTTP POST e grava o áudio retornado em `output_wav_path`.
    Retorna True se OK, False em caso de erro.
    """
    if not SPEECHIFY_API_KEY:
        logger.warning("SPEECHIFY_API_KEY não definido. Pulando TTS.")
        return False

    payload = {
        "voice_id": VOICE_ID,
        "text": text,
        "language": language
    }
    headers = {
        "Authorization": f"Bearer {SPEECHIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(SPEECHIFY_TTS_ENDPOINT, json=payload, headers=headers, stream=True)
    if response.status_code == 200:
        # Grava o conteúdo binário (wav/mp3, dependendo da API) em disco
        with open(output_wav_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"[TTS] Áudio Speechify salvo em {output_wav_path}")
        return True
    else:
        logger.error(f"[TTS] Erro Speechify ({response.status_code}): {response.text}")
        return False


def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Gera TTS com Speechify (via HTTP).
      5. Converte para MP3, concatena no concat.mp3 e empacota em HLS.
    """

    # 1) Carrega o modelo Whisper (usar base; ajustável)
    model = whisper.load_model("base")

    processed = set()

    # Antes de começar, crie/limpe a pasta “processed” dentro de audio_dir
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Cria um “concat.mp3” inicial vazio (silêncio) para não falhar no primeiro append
    concat_path = os.path.join(processed_dir, "concat.mp3")
    if os.path.exists(concat_path):
        os.remove(concat_path)
    # Gera um arquivo MP3 vazio de 1 segundo ou silêncio (ou simplesmente um anullsrc para iniciá-lo)
    # Aqui usamos ffmpeg para gerar um “silêncio” de 0.5s (evita erro de concat vazio)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "0.5",
            "-q:a", "9",
            concat_path
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    logger.info(f"[worker] Arquivo inicial de concat.mp3 criado em {concat_path}")

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"[worker] Processando segmento: {wav_path}")

            try:
                # 2) Transcrição com Whisper
                logger.info(f"[worker] Transcrevendo {wav_path} com idioma forçado para português...")
                result = model.transcribe(wav_path, language="pt")
                text = result["text"].strip()
                logger.info(f"[worker] Transcrição: {text}")

                # 3) Tradução com DeepL
                logger.info(f"[worker] Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                logger.info(f"[worker] Tradução: {translated}")

                # 4) Síntese de voz com Speechify
                output_speechify_wav = wav_path.replace(".wav", f"_{lang}.wav")
                logger.info(f"[worker] Sintetizando texto traduzido com Speechify ...")
                ok = text_to_speech_with_speechify(translated, output_speechify_wav, language=lang)
                if not ok:
                    logger.error(f"[worker] Falha ao sintetizar TTS para {wav_path}, pulando.")
                    processed.add(filename)
                    continue

                # 5) Converte WAV → MP3
                output_mp3 = output_speechify_wav.replace(".wav", ".mp3")
                logger.info(f"[worker] Convertendo WAV para MP3: {output_speechify_wav} -> {output_mp3}")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", output_speechify_wav, "-q:a", "4", output_mp3],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                logger.info(f"[worker] Arquivo convertido para MP3: {output_mp3}")

                # 6) Concatena no concat.mp3
                logger.info(f"[worker] Adicionando segmento ao arquivo contínuo: {concat_path}")
                # Cria um arquivo temporário
                temp_concat = concat_path + ".temp"
                # Usa concat demuxer do ffmpeg
                concat_input = f"concat:{concat_path}|{output_mp3}"
                result = subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", concat_input,
                        "-c", "copy",
                        temp_concat
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if result.returncode != 0:
                    stderr = result.stderr.decode("utf-8", errors="ignore")
                    logger.error(f"[worker] Erro ao executar ffmpeg concat: {stderr}")
                else:
                    # Substitui o antigo concat.mp3 pelo novo
                    shutil.move(temp_concat, concat_path)
                    logger.info(f"[worker] concat.mp3 atualizado com sucesso.")

                # 7) Empacotar em HLS via FFmpeg
                channel = os.path.basename(audio_dir)
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                logger.info(f"[worker] Convertendo {concat_path} para HLS em {output_index} ...")
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", concat_path,
                        "-c:a", "aac", "-b:a", "128k",
                        "-vn",
                        "-hls_time", "10",
                        "-hls_playlist_type", "event",
                        "-hls_segment_filename", ts_pattern,
                        output_index
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                logger.info(f"[worker] HLS gerado em {output_index}")

                processed.add(filename)

            except Exception as e:
                logger.error(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
