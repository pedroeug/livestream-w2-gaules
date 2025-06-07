# pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator, GoogleTranslator
import requests
import subprocess
from queue import Queue

def worker_loop(audio_dir: str, lang: str, log_queue: Queue):
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
    speechify_voice_id = os.getenv("SPEECHIFY_VOICE_ID", "").strip()  # ex: "3af44bf3-..."
    if not speechify_key or not speechify_voice_id:
        log_queue.put("[worker] AVISO: SPEECHIFY_API_KEY ou SPEECHIFY_VOICE_ID não definido. TTS será pulado.")
    else:
        log_queue.put("[worker] Speechify configurado corretamente.")

    deepl_key = os.getenv("DEEPL_API_KEY", "").strip()
    if deepl_key:
        log_queue.put("[worker] DeepL configurado corretamente.")
    else:
        log_queue.put("[worker] AVISO: DEEPL_API_KEY não definido. Usando Google Translate.")

    processed = set()

    while True:
        # 3) Para cada arquivo .wav não processado:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
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
                try:
                    if deepl_key:
                        translator = DeeplTranslator(api_key=deepl_key, source="auto", target=lang)
                    else:
                        translator = GoogleTranslator(source="auto", target=lang)
                    translated = translator.translate(text)
                except Exception as e:
                    log_queue.put(f"[worker] Erro na tradução: {e}. Usando texto original.")
                    translated = text
                log_queue.put(f"[worker] Tradução: {translated}")

                # --- Síntese Speechify (via HTTP) ---
                if speechify_key and speechify_voice_id:
                    log_queue.put("[worker] Sintetizando com Speechify ...")
                    # Monta payload para Speechify:
                    headers = {
                        "Authorization": f"Bearer {speechify_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "voiceId": speechify_voice_id,
                        "input": translated
                    }
                    # Faz request:
                    response = requests.post(
                        "https://api.sws.speechify.com/v1/tts/audio",
                        json=payload,
                        headers=headers
                    )
                    if response.status_code != 200:
                        log_queue.put(f"[worker] Erro Speechify ({response.status_code}): {response.text}")
                        processed.add(filename)
                        continue

                    audio_data_base64 = response.json().get("audioData")
                    if not audio_data_base64:
                        log_queue.put(f"[worker] Erro: resposta Speechify sem campo audioData.")
                        processed.add(filename)
                        continue

                    # Converte base64 → binário e salva em wav temporário:
                    from base64 import b64decode
                    temp_wav = wav_path.replace(".wav", f"_{lang}.wav")
                    with open(temp_wav, "wb") as f:
                        f.write(b64decode(audio_data_base64))
                    log_queue.put(f"[worker] Áudio Speechify salvo em {temp_wav}")
                else:
                    log_queue.put(
                        "[worker] Pulando síntese: credenciais Speechify não configuradas. Usando áudio original."
                    )
                    temp_wav = wav_path

                # --- Converte wav para mp3 (para concatenar) ---
                log_queue.put(f"[worker] Convertendo WAV para MP3: {temp_wav}")
                mp3_path = temp_wav.replace(".wav", ".mp3")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", temp_wav, "-codec:a", "libmp3lame", mp3_path],
                    check=True
                )
                log_queue.put(f"[worker] MP3 gerado: {mp3_path}")

                # --- Concatena no “concat.mp3” contínuo ---
                channel = os.path.basename(audio_dir)
                processed_dir = os.path.join(audio_dir, "processed")
                os.makedirs(processed_dir, exist_ok=True)
                concat_mp3 = os.path.join(processed_dir, "concat.mp3")
                if not os.path.exists(concat_mp3):
                    # Se não existe, cria um mp3 vazio com um segundo de silêncio
                    silent = os.path.join(processed_dir, "silent.wav")
                    subprocess.run(
                        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", 
                         "-t", "0.1", "-q:a", "9", silent],
                        check=True
                    )
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", silent, "-codec:a", "libmp3lame", concat_mp3],
                        check=True
                    )
                    log_queue.put(f"[worker] Arquivo inicial concat.mp3 criado em {concat_mp3}")

                # Agora concatena: concat|novo → temp → substitui
                log_queue.put(f"[worker] Adicionando {mp3_path} ao concat.mp3")
                temp_out = concat_mp3 + ".temp"
                subprocess.run(
                    ["ffmpeg", "-y", "-i", f"concat:{concat_mp3}|{mp3_path}", "-acodec", "copy", temp_out],
                    check=True
                )
                os.replace(temp_out, concat_mp3)
                log_queue.put(f"[worker] concat.mp3 atualizado com {mp3_path}")

                # --- Gera HLS ---
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)
                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")
                log_queue.put(f"[worker] Gerando HLS em {output_index} ...")
                subprocess.run([
                    "ffmpeg", "-y", "-i", concat_mp3,
                    "-c:a", "aac", "-b:a", "128k", "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    output_index
                ], check=True)
                log_queue.put(f"[worker] HLS gerado em {output_index}")

                processed.add(filename)

            except Exception as e:
                log_queue.put(f"[worker] ERRO ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
