# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
import logging
import subprocess
from deep_translator import DeeplTranslator
import requests

logger = logging.getLogger("worker")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def worker_loop(audio_dir: str, processed_dir: str, lang: str, hls_dir: str):
    model = whisper.load_model("base")

    coqui_api_key = os.getenv("COQUI_API_KEY")
    if not coqui_api_key:
        logger.warning("COQUI_API_KEY não definido. Não será possível usar Coqui TTS.")

    voice_sample_path = "backend/assets/voices/gaules_sample.wav"

    concat_mp3 = os.path.join(processed_dir, "concat.mp3")
    if not os.path.exists(concat_mp3):
        silence_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1",
            "-q:a", "9",
            "-acodec", "libmp3lame",
            concat_mp3
        ]
        subprocess.run(silence_cmd, check=True)
        logger.info(f"Arquivo inicial de concat.mp3 criado em {concat_mp3}")

    processed_wavs = set()

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed_wavs:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"Processando segmento: {wav_path}")

            try:
                logger.info(f"Transcrevendo {wav_path} com idioma forçado para português...")
                result = model.transcribe(wav_path, language="pt")
                original_text = result["text"].strip()
                logger.info(f"Transcrição: {original_text}")

                logger.info(f"Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="pt", target=lang)
                translated = translator.translate(original_text)
                logger.info(f"Tradução: {translated}")

                logger.info("Sintetizando texto traduzido com Coqui TTS ...")
                data = {"text": translated, "voice": "tts_models/multilingual/vctk/vits"} if lang == "en" else {"text": translated, "voice": "tts_models/en/ljspeech"}
                headers = {"accept": "application/json", "xi-api-key": coqui_api_key}

                response = requests.post("https://api.coqui.ai/tts/inference", headers=headers, json=data)
                if response.status_code == 200:
                    synthesized_wav = os.path.join(processed_dir, filename.replace(".wav", f"_{lang}.wav"))
                    with open(synthesized_wav, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Áudio sintetizado salvo em {synthesized_wav}")
                else:
                    raise RuntimeError(f"Coqui TTS retornou {response.status_code}: {response.text}")

                mp3_filename = filename.replace(".wav", f"_{lang}.mp3")
                mp3_path = os.path.join(processed_dir, mp3_filename)
                logger.info(f"Convertendo WAV para MP3: {synthesized_wav} → {mp3_path}")
                convert_cmd = [
                    "ffmpeg", "-y",
                    "-i", synthesized_wav,
                    "-codec:a", "libmp3lame",
                    "-b:a", "128k",
                    mp3_path
                ]
                subprocess.run(convert_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"Arquivo convertido para MP3: {mp3_path}")

                new_concat = os.path.join(processed_dir, "concat.mp3.temp")
                concat_cmd = [
                    "ffmpeg", "-y",
                    "-i", f"concat:{concat_mp3}|{mp3_path}",
                    "-c", "copy",
                    new_concat
                ]
                try:
                    subprocess.run(concat_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    os.replace(new_concat, concat_mp3)
                    logger.info(f"Adicionou {mp3_path} a {concat_mp3}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Erro ao executar ffmpeg concat: {e.stderr.decode().strip()}")
                    if os.path.exists(new_concat):
                        os.remove(new_concat)

                hls_index = os.path.join(hls_dir, "index.m3u8")
                ts_pattern = os.path.join(hls_dir, "%03d.ts")

                hls_cmd = [
                    "ffmpeg", "-y",
                    "-i", concat_mp3,
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    hls_index
                ]
                subprocess.run(hls_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"HLS atualizado em {hls_index}")

                processed_wavs.add(filename)

            except Exception as e:
                logger.error(f"Erro ao processar {wav_path}: {e}")
                processed_wavs.add(filename)

        time.sleep(1)
