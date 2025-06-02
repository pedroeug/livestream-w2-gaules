# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess
import logging
from speechify_api import SpeechifyClient, VoiceModel  # SDK oficial Speechify

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("worker")


def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos .wav em audio_dir.
      2. Transcreve (Whisper), traduz (DeepL), sintetiza (Speechify) -> MP3.
      3. Concatena segmentos MP3 em audio_segments/{channel}/processed/concat.mp3.
      4. Gera HLS em hls/{channel}/{lang}/index.m3u8 + .ts.
    """

    # Carrega modelo Whisper
    model = whisper.load_model("base")

    # Inicializa Speechify
    speechify_api_key = os.getenv("SPEECHIFY_API_KEY")
    speechify_voice_id = os.getenv("SPEECHIFY_VOICE_ID")
    if not speechify_api_key or not speechify_voice_id:
        logger.warning("SPEECHIFY_API_KEY ou SPEECHIFY_VOICE_ID não definido! TTS falhará.")
        return

    client = SpeechifyClient(api_key=speechify_api_key)
    voice_model = VoiceModel(voice_id=speechify_voice_id, audio_format="mp3")

    channel = os.path.basename(audio_dir)
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Cria arquivo inicial de concatenação com 1 seg de silêncio (precisa existir antes de concat)
    concat_path = os.path.join(processed_dir, "concat.mp3")
    if not os.path.exists(concat_path):
        # Gera 1 segundo de silêncio em MP3:
        # usamos "anullsrc" do FFmpeg para gerar um MP3 vazio
        cmd_init = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1",
            "-c:a", "libmp3lame", "-ar", "16000", "-ac", "1",
            concat_path
        ]
        subprocess.run(cmd_init, check=True)
        logger.info(f"[worker] Arquivo inicial de silêncio criado em {concat_path}")

    processed_wavs = set()

    while True:
        # Procura novos .wav
        for fname in sorted(os.listdir(audio_dir)):
            if not fname.endswith(".wav") or fname in processed_wavs:
                continue

            wav_path = os.path.join(audio_dir, fname)
            logger.info(f"[worker] Encontrou segmento: {wav_path}")

            try:
                # 1) Transcrição com Whisper (forçando português de entrada)
                logger.info(f"[worker] Transcrevendo {wav_path} (pt)...")
                result = model.transcribe(wav_path, language="pt")
                text_pt = result["text"].strip()
                logger.info(f"[worker] Transcrição (pt): {text_pt}")

                # 2) Tradução com DeepL
                logger.info(f"[worker] Traduzindo para '{lang}'...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text_pt)
                logger.info(f"[worker] Tradução ({lang}): {translated}")

                # 3) TTS Speechify -> gera MP3 direto
                out_mp3 = os.path.join(processed_dir, fname.replace(".wav", f"_{lang}.mp3"))
                logger.info(f"[worker] Sintetizando com Speechify -> {out_mp3} ...")
                client.text_to_speech(
                    text=translated,
                    voice_model=voice_model,
                    output=out_mp3
                )
                logger.info(f"[worker] MP3 sintetizado salvo em {out_mp3}")

                # 4) Concatenação progressiva em concat.mp3
                logger.info("[worker] Concatenação progressiva de MP3...")
                tmp_concat = concat_path + ".tmp"
                concat_input = f"concat:{concat_path}|{out_mp3}"
                ffmpeg_cat = [
                    "ffmpeg", "-y",
                    "-i", concat_input,
                    "-c", "copy",
                    tmp_concat
                ]
                subprocess.run(ffmpeg_cat, check=True)
                os.replace(tmp_concat, concat_path)
                logger.info(f"[worker] Arquivo contínuo atualizado: {concat_path}")

                # 5) Gera/atualiza HLS em hls/{channel}/{lang}/
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)
                hls_index = os.path.join(hls_dir, "index.m3u8")
                ts_pattern = os.path.join(hls_dir, "%03d.ts")

                logger.info(f"[worker] Gerando HLS em {hls_index} ...")
                ffmpeg_hls = [
                    "ffmpeg", "-y",
                    "-i", concat_path,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    hls_index
                ]
                subprocess.run(ffmpeg_hls, check=True)
                logger.info(f"[worker] HLS gerado em {hls_index}")

                processed_wavs.add(fname)

            except Exception as e:
                logger.error(f"[worker] Erro ao processar {wav_path}: {e}")
                processed_wavs.add(fname)
                continue

        time.sleep(1)
