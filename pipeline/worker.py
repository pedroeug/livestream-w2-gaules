# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess
import logging

# Import do cliente Speechify SWS
from speechify_sws import SpeechifyClient

logger = logging.getLogger("worker")
logger.setLevel(logging.INFO)


def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Síntese de voz (Speechify SWS).
      5. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # 1) Carrega o modelo Whisper
    logger.info("[worker] Carregando modelo Whisper...")
    model = whisper.load_model("base")

    # 2) Inicializa cliente Speechify SWS a partir de variável de ambiente
    sws_key = os.getenv("SWS_API_KEY")
    if not sws_key:
        logger.error("[worker] ERRO: SWS_API_KEY não definido. TTS será pulado.")
        return

    sws = SpeechifyClient(api_key=sws_key)
    # O voice_id fornecido
    voice_id = "3af44bf3-439e-4e9d-a6ff-4870d437ef7a"

    processed = set()

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"[worker] Encontrou novo segmento: {wav_path}")

            try:
                # === 1) Transcrição com Whisper ===
                logger.info(f"[worker] Transcrevendo {wav_path} ...")
                result = model.transcribe(wav_path)
                text = result["text"].strip()
                logger.info(f"[worker] Transcrição: {text}")

                # === 2) Tradução com DeepL ===
                logger.info(f"[worker] Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                logger.info(f"[worker] Tradução: {translated}")

                # === 3) Síntese de voz com Speechify SWS ===
                logger.info(f"[worker] Sintetizando texto com Speechify (voice_id={voice_id}) ...")
                output_mp3 = wav_path.replace(".wav", f"_{lang}.mp3")
                sws.tts_to_file(
                    text          = translated,
                    voice_id      = voice_id,
                    language      = lang,
                    file_path     = output_mp3,
                    output_format = "mp3"
                )
                logger.info(f"[worker] Áudio sintetizado salvo em {output_mp3}")

                # === 4) Empacotar em HLS via ffmpeg ===
                channel = os.path.basename(audio_dir)
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                logger.info(f"[worker] Convertendo {output_mp3} para HLS em {output_index} ...")
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", output_mp3,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    output_index
                ]
                subprocess.run(ffmpeg_cmd, check=True)
                logger.info(f"[worker] HLS gerado em {output_index}")

                processed.add(filename)

            except Exception as e:
                logger.error(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
