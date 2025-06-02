# livestream-w2-gaules/pipeline/worker.py

import os
import time
import logging
import whisper
from deep_translator import DeeplTranslator
import subprocess

from speechify_api import SpeechifyClient, VoiceModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1) Monitora novos arquivos .wav em audio_dir.
      2) Transcreve usando Whisper.
      3) Traduz a transcrição (DeepL).
      4) Sintetiza voz com Speechify (voice cloning se lang=='en').
      5) Adiciona ao concat.mp3 e empacota em HLS.
    """

    # Carrega modelo Whisper
    model = whisper.load_model("base")

    # Inicializa client Speechify (leitura de chave de ambiente)
    coqui_api_key = os.getenv("COQUI_API_KEY", None)
    speechify_key = os.getenv("SPEECHIFY_API_KEY", None)
    if not speechify_key:
        logger.warning("SPEECHIFY_API_KEY não definido; TTS Speechify não será usado.")
    else:
        client = SpeechifyClient(api_key=speechify_key)

    processed = set()

    # Pasta de “processed” onde ficarão MP3
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Cria arquivo inicial concat.mp3 a partir de silêncio, para evitar erro no ffmpeg concat
    silent_mp3 = os.path.join(processed_dir, "concat.mp3")
    if not os.path.exists(silent_mp3):
        # Gera 1 segundo de silêncio em MP3 (16000 Hz mono)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1",
            "-q:a", "9",
            silent_mp3
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"[worker] Arquivo inicial de concat.mp3 criado em {silent_mp3}")

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"[worker] Processando segmento: {wav_path}")

            try:
                # --- 1) Transcrição Whisper (forçando pt para EN se necessário) ---
                detect_language = "pt"  # a Twitch do Gaules fala em PT
                logger.info(f"[worker] Transcrevendo {wav_path} com idioma forçado para '{detect_language}'...")
                result = model.transcribe(wav_path, language=detect_language)
                text = result["text"].strip()
                logger.info(f"[worker] Transcrição: {text}")

                # --- 2) Tradução via DeepL ---
                logger.info(f"[worker] Traduzindo para '{lang}' ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                logger.info(f"[worker] Tradução: {translated}")

                # --- 3) Síntese de voz com Speechify ---
                if speechify_key:
                    logger.info("[worker] Sintetizando com Speechify SWS ...")

                    # Escolha do modelo de voz
                    # Vamos usar voice_id fixo (o ID que você forneceu) e caso lang != 'en', usa-se um modelo single‐speaker padrão
                    if lang == "en":
                        voice_model = VoiceModel(id="3af44bf3-439e-4e9d-a6ff-4870d437ef7a")
                        logger.info("[worker] Usando voice cloning (voice_id) para EN")
                        tts_wav = client.text_to_speech(
                            text=translated,
                            voice=voice_model,
                            format="wav", 
                            sample_rate=16000
                        )
                    else:
                        # Para outros idiomas, Speechify pode ter modelo padrão; exemplo:
                        voice_model = VoiceModel(id="text_to_speech_default_16khz")
                        logger.info(f"[worker] Usando modelo padrão para TTS em '{lang}'")
                        tts_wav = client.text_to_speech(
                            text=translated,
                            voice=voice_model,
                            format="wav",
                            sample_rate=16000
                        )

                    # Salva o WAV retornado pelo Speechify
                    output_wav = os.path.join(processed_dir, filename.replace(".wav", f"_{lang}.wav"))
                    with open(output_wav, "wb") as f:
                        f.write(tts_wav.read())
                    logger.info(f"[worker] Áudio sintetizado salvo em {output_wav}")

                else:
                    logger.warning("[worker] Pulando TTS Speechify: SPEECHIFY_API_KEY não configurada.")
                    processed.add(filename)
                    continue

                # --- 4) Converte o WAV gerado (Speechify) para MP3  ---
                mp3_path = output_wav.replace(".wav", ".mp3")
                logger.info(f"[worker] Convertendo WAV -> MP3: {output_wav} -> {mp3_path}")
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", output_wav,
                    "-q:a", "5",
                    "-ac", "1",
                    "-ar", "16000",
                    mp3_path
                ]
                subprocess.run(ffmpeg_cmd, check=True)
                logger.info(f"[worker] Arquivo convertido para MP3: {mp3_path}")

                # --- 5) Concatena este MP3 no concat.mp3 existente ---
                concat_in = os.path.join(processed_dir, "concat.mp3")
                temp_concat = concat_in + ".temp"

                logger.info(f"[worker] Adicionando segmento ao concat.mp3 existentes ...")
                concat_cmd = [
                    "ffmpeg", "-y",
                    "-i", f"concat:{concat_in}|{mp3_path}",
                    "-c", "copy",
                    temp_concat
                ]
                subprocess.run(concat_cmd, check=True)
                # Substitui o antigo concat.mp3 pelo novo
                os.replace(temp_concat, concat_in)
                logger.info(f"[worker] Segmento adicionado em {concat_in}")

                # --- 6) Empacota o concat.mp3 completo em HLS (ts + index.m3u8) ---
                channel = os.path.basename(audio_dir)
                hls_output_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_output_dir, exist_ok=True)
                ts_pattern = os.path.join(hls_output_dir, "%03d.ts")
                index_file = os.path.join(hls_output_dir, "index.m3u8")

                logger.info(f"[worker] Empacotando HLS: {concat_in} → {index_file}")
                hls_cmd = [
                    "ffmpeg", "-y",
                    "-i", concat_in,
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    index_file
                ]
                subprocess.run(hls_cmd, check=True)
                logger.info(f"[worker] HLS gerado em {index_file}")

                # Marca como processado
                processed.add(filename)

            except Exception as e:
                logger.error(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)  # espera 1s antes de checar novamente
