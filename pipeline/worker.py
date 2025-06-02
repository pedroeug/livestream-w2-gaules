# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess
import logging
from speechify_api import SpeechifyClient, VoiceModel  # import do SDK oficial

logger = logging.getLogger("worker")
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Carrega credenciais do Speechify via variáveis de ambiente
SPEECHIFY_API_KEY = os.getenv("SPEECHIFY_API_KEY", None)
SPEECHIFY_VOICE_ID = os.getenv("SPEECHIFY_VOICE_ID", None)
# Exemplo: SPEECHIFY_VOICE_ID="3af44bf3-439e-4e9d-a6ff-4870d437ef7a"

if not SPEECHIFY_API_KEY or not SPEECHIFY_VOICE_ID:
    logger.warning("[worker] SPEECHIFY_API_KEY ou SPEECHIFY_VOICE_ID não definido. TTS falhará.")


def synthesize_with_speechify(text: str, output_path: str, voice_id: str):
    """
    Usa o SDK oficial `speechify-api` para gerar um MP3 a partir de `text` e `voice_id`.
    Salva os bytes de áudio em `output_path`.
    """
    if not SPEECHIFY_API_KEY or not voice_id:
        raise RuntimeError("Credenciais do Speechify ausentes.")

    # Inicializa o cliente
    client = SpeechifyClient(api_key=SPEECHIFY_API_KEY)
    # Chama TTS (formato mp3)
    # A documentação do SDK diz algo como: client.text_to_speech(...)
    logger.info(f"[worker] Chamando SpeechifyClient.text_to_speech para voice_id={voice_id}")
    response = client.text_to_speech(
        text=text,
        voice_id=voice_id,
        format="mp3"
    )

    # O SDK retorna bytes de MP3 em response.audio
    audio_bytes = response.audio
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
    logger.info(f"[worker] Áudio Speechify salvo em {output_path}")


def worker_loop(channel: str, audio_dir: str, lang: str):
    """
    Loop que:
    1) Monitora novos arquivos WAV em audio_dir
    2) Transcreve com Whisper (forçando pt)
    3) Traduz com DeepL para `lang`
    4) Sintetiza voz em MP3 via Speechify SDK
    5) Concatena em concat.mp3 contínuo
    6) Gera HLS em hls/{channel}/{lang}/index.m3u8
    """
    model = whisper.load_model("base")

    processed = set()
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Cria um concat.mp3 inicial (silêncio), para que o ffmpeg HLS tenha algo
    concat_mp3 = os.path.join(processed_dir, "concat.mp3")
    if not os.path.isfile(concat_mp3):
        logger.info("[worker] Criando concat.mp3 inicial com 1 segundo de silêncio")
        temp_silence = os.path.join(processed_dir, "silence.wav")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1",
            "-acodec", "pcm_s16le",
            temp_silence
        ], check=True)
        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_silence,
            "-codec:a", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            concat_mp3
        ], check=True)
        os.remove(temp_silence)
        logger.info(f"[worker] concat.mp3 inicial criado em {concat_mp3}")

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"[worker] Novo segmento detectado: {wav_path}")

            try:
                # 1) Transcrição com Whisper (força pt)
                logger.info(f"[worker] Transcrevendo {wav_path} (lingua pt)...")
                result = model.transcribe(wav_path, language="pt")
                orig_text = result["text"].strip()
                logger.info(f"[worker] Texto transcrito: {orig_text}")

                # 2) Tradução com DeepL
                logger.info(f"[worker] Traduzindo para '{lang}' ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(orig_text)
                logger.info(f"[worker] Texto traduzido: {translated}")

                # 3) Sintetiza MP3 com Speechify SDK
                if SPEECHIFY_API_KEY and SPEECHIFY_VOICE_ID:
                    segment_id = os.path.splitext(filename)[0]
                    tts_mp3 = os.path.join(processed_dir, f"dubbed_{segment_id}.mp3")
                    synthesize_with_speechify(translated, tts_mp3, SPEECHIFY_VOICE_ID)
                else:
                    raise RuntimeError("Credenciais do Speechify ausentes. Pulando TTS.")

                # 4) Concatena o novo MP3 em concat.mp3
                logger.info(f"[worker] Adicionando {tts_mp3} ao concat.mp3")
                tmp_concat = concat_mp3 + ".tmp.mp3"
                concat_input = f"concat:{concat_mp3}|{tts_mp3}"
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", concat_input,
                    "-c", "copy",
                    tmp_concat
                ], check=True)
                os.replace(tmp_concat, concat_mp3)
                logger.info(f"[worker] concat.mp3 atualizado.")

                # 5) Regenera HLS a partir de concat.mp3
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)
                hls_index = os.path.join(hls_dir, "index.m3u8")
                ts_pattern = os.path.join(hls_dir, "%05d.ts")

                logger.info(f"[worker] Gerando HLS em {hls_index} ...")
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", concat_mp3,
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    hls_index
                ], check=True)
                logger.info(f"[worker] Playlist HLS atualizada.")

                processed.add(filename)

            except Exception as e:
                logger.error(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
