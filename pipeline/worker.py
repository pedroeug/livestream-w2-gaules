# pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator, GoogleTranslator
from speechify import Speechify
from speechify.core.api_error import ApiError
import subprocess
from queue import Queue
import threading

def worker_loop(audio_dir: str, lang: str, log_queue: Queue, stop_event: threading.Event):
    """
    Loop contínuo que:
      1. Monitora novos .wav em audio_dir
      2. Transcreve com Whisper
      3. Traduz com DeepL
      4. Sintetiza com Speechify (ou Coqui, se quiser)
      5. Gera HLS em hls/{channel}/{lang}/
      6. Cada passo envia uma mensagem para log_queue.put("texto")
    """
    # 1) Carrega o modelo Whisper
    model = whisper.load_model("base")
    log_queue.put("[worker] Modelo Whisper carregado (base).")

    # 2) Configura credenciais Speechify (via env var SPEECHIFY_API_KEY)
    speechify_key = os.getenv("SPEECHIFY_API_KEY", "").strip()
    speechify_voice_id = os.getenv("SPEECHIFY_VOICE_ID", "").strip()
    speechify_client = None
    if not speechify_key or not speechify_voice_id:
        log_queue.put("[worker] AVISO: SPEECHIFY_API_KEY ou SPEECHIFY_VOICE_ID não definido. TTS será pulado.")
    else:
        try:
            speechify_client = Speechify(token=speechify_key)
            log_queue.put("[worker] Speechify configurado corretamente.")
        except Exception as e:
            log_queue.put(f"[worker] Erro ao inicializar Speechify: {e}. TTS será pulado.")
            speechify_client = None

    deepl_key = os.getenv("DEEPL_API_KEY", "").strip()
    if deepl_key:
        log_queue.put("[worker] DeepL configurado corretamente.")
    else:
        log_queue.put("[worker] AVISO: DEEPL_API_KEY não definido. Usando Google Translate.")

    processed = set()
    channel = os.path.basename(os.path.abspath(audio_dir))
    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)
    playlist = os.path.join(hls_dir, "index.m3u8")
    if not os.path.exists(playlist):
        with open(playlist, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:30\n#EXT-X-MEDIA-SEQUENCE:0\n")
    seq = 0
    skip_first = True  # ignora o primeiro segmento capturado

    while not stop_event.is_set():
        # 3) Para cada arquivo .wav não processado:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            if skip_first:
                processed.add(filename)
                skip_first = False
                continue

            wav_path = os.path.join(audio_dir, filename)
            log_queue.put(f"[worker] Encontrado novo segmento: {wav_path}")

            try:
                # --- Transcrição ---
                log_queue.put(f"[worker] Transcrevendo {wav_path} ...")
                result = model.transcribe(wav_path, language="pt")  # força Português
                text = result["text"].strip()
                log_queue.put(f"[worker] Transcrição: {text}")

                # --- Tradução ---
                log_queue.put(f"[worker] Traduzindo para {lang} ...")
                translated = text
                try:
                    if deepl_key:
                        # DeepL não aceita "auto" como source_lang via API.
                        # Como a transcrição sempre retorna português,
                        # informamos explicitamente "pt".
                        translator = DeeplTranslator(api_key=deepl_key, source="pt", target=lang, timeout=5)
                        translated = translator.translate(text)
                    else:
                        translator = GoogleTranslator(source="auto", target=lang, timeout=5)
                        translated = translator.translate(text)
                except Exception as e:
                    log_queue.put(f"[worker] Erro na tradução com DeepL: {e}.")
                    if deepl_key:
                        log_queue.put("[worker] Tentando Google Translate ...")
                        try:
                            translator = GoogleTranslator(source="auto", target=lang, timeout=5)
                            translated = translator.translate(text)
                        except Exception as e2:
                            log_queue.put(f"[worker] Falha no Google Translate: {e2}. Usando texto original.")
                            translated = text
                log_queue.put(f"[worker] Tradução: {translated}")

                # --- Síntese com Speechify ---
                if speechify_client:
                    log_queue.put("[worker] Sintetizando com Speechify ...")
                    try:
                        response = speechify_client.tts.audio.speech(
                            input=translated,
                            voice_id=speechify_voice_id,
                            audio_format="wav"
                        )
                        audio_data_base64 = response.audio_data
                    except ApiError as e:
                        detail = str(e.body)[:200] if hasattr(e, 'body') else str(e)
                        log_queue.put(f"[worker] Erro Speechify ({e.status_code}): {detail}")
                        audio_data_base64 = None
                    except Exception as e:
                        log_queue.put(f"[worker] Erro inesperado Speechify: {e}")
                        audio_data_base64 = None

                    if audio_data_base64:
                        from base64 import b64decode
                        temp_wav = wav_path.replace(".wav", f"_{lang}.wav")
                        with open(temp_wav, "wb") as f:
                            f.write(b64decode(audio_data_base64))
                        log_queue.put(f"[worker] Áudio Speechify salvo em {temp_wav}")
                    else:
                        log_queue.put("[worker] Falha na síntese. Usando áudio original.")
                        temp_wav = wav_path
                else:
                    log_queue.put(
                        "[worker] Pulando síntese: credenciais Speechify não configuradas. Usando áudio original."
                    )
                    temp_wav = wav_path

                # --- Converte áudio para segmento TS ---
                out_ts = os.path.join(hls_dir, filename.replace(".wav", ".ts"))
                subprocess.run([
                    "ffmpeg", "-y", "-i", temp_wav, "-c:a", "aac", "-b:a", "128k",
                    "-f", "mpegts", out_ts
                ], check=True)
                with open(playlist, "a") as pl:
                    pl.write(f"#EXTINF:30.0,\n{os.path.basename(out_ts)}\n")
                seq += 1
                log_queue.put(f"[worker] Segmento gerado: {out_ts}")

                processed.add(filename)
                dest_wav = os.path.join(audio_dir, "processed", filename)
                os.makedirs(os.path.dirname(dest_wav), exist_ok=True)
                try:
                    os.replace(wav_path, dest_wav)
                except Exception:
                    pass

            except Exception as e:
                log_queue.put(f"[worker] ERRO ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)

    log_queue.put("[worker] Loop finalizado")
