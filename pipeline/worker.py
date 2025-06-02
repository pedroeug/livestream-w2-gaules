# pipeline/worker.py

import os
import time
import whisper
import base64
import requests
import subprocess
from deep_translator import DeeplTranslator

# ========== CONFIGURAÇÃO DO SPEECHIFY ==========
# Sua chave de API do Speechify (defina em SPEECHIFY_API_KEY no ambiente)
API_KEY = os.getenv("SPEECHIFY_API_KEY", "")
# O Voice ID que você quer usar (voz clonada do Gaules, por exemplo)
VOICE_ID = "3af44bf3-439e-4e9d-a6ff-4870d437ef7a"
# Endpoint base do Speechify TTS REST
SPEECHIFY_URL = "https://api.speechify.com/v1/tts/audio/speech"
# ===============================================

def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que faz:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve com Whisper (forçando português no exemplo).
      3. Traduz para o idioma 'lang' via DeepL.
      4. Chama o endpoint REST do Speechify para gerar MP3 base64.
      5. Decodifica e salva cada segmento como MP3.
      6. Concatena todos os MP3s num único concat.mp3 contínuo.
      7. Gera HLS (index.m3u8 + .ts) a partir do concat.mp3.
    """

    # 1) Carrega o modelo Whisper "base" (produzido pela OpenAI).
    model = whisper.load_model("base")

    # Conjunto para marcar quais arquivos já foram processados
    processed = set()

    # Cria pasta "processed" dentro de audio_dir, onde serão salvos os MP3s e o concat.mp3
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Caminho absoluto para o MP3 contínuo inicial
    concat_mp3 = os.path.join(processed_dir, "concat.mp3")
    # Se não existe ainda, cria um MP3 mínimo (silêncio de 0.1s) para evitar erro de concat
    if not os.path.exists(concat_mp3):
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-c:a", "libmp3lame", "-b:a", "128k",
            "-t", "0.1",
            concat_mp3
        ], check=True)

    while True:
        # 2) Varre todos os WAVs na pasta, em ordem alfabética
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            print(f"[worker] Processando segmento: {wav_path}")

            try:
                # --- Transcrição via Whisper (forçando PT) ---
                print(f"[worker] Transcrevendo (PT) {wav_path} ...")
                result = model.transcribe(wav_path, language="pt")
                text_pt = result["text"].strip()
                print(f"[worker] Texto extraído (PT): {text_pt}")

                # --- Tradução via DeepL ---
                print(f"[worker] Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text_pt)
                print(f"[worker] Texto traduzido ({lang}): {translated}")

                # --- Chamada HTTP ao Speechify (gera MP3 base64) ---
                if not API_KEY:
                    raise RuntimeError("SPEECHIFY_API_KEY não definido no ambiente")
                print("[worker] Chamando Speechify REST para TTS (MP3 base64) ...")
                payload = {
                    "voiceId": VOICE_ID,
                    "input": translated
                }
                headers = {
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                }
                resp = requests.post(SPEECHIFY_URL, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()

                data = resp.json()
                audio_base64 = data.get("audioData")
                if not audio_base64:
                    raise RuntimeError("Resposta Speechify não retornou audioData")

                # Decode do base64 para bytes MP3
                audio_bytes = base64.b64decode(audio_base64)

                # Salva o MP3 do segmento gerado
                dubbed_mp3 = os.path.join(
                    processed_dir,
                    filename.replace(".wav", f"_{lang}.mp3")
                )
                with open(dubbed_mp3, "wb") as f:
                    f.write(audio_bytes)
                print(f"[worker] Áudio MP3 salvo em: {dubbed_mp3}")

                # --- Concatena ao MP3 contínuo existente ---
                temp_concat = concat_mp3 + ".temp.mp3"
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", f"concat:{concat_mp3}|{dubbed_mp3}",
                    "-c", "copy",
                    temp_concat
                ], check=True)
                os.replace(temp_concat, concat_mp3)
                print(f"[worker] Arquivo contínuo atualizado: {concat_mp3}")

                # --- Geração de HLS (m3u8 + .ts) a partir do MP3 contínuo ---
                channel = os.path.basename(os.path.dirname(audio_dir))
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                index_m3u8 = os.path.join(hls_dir, "index.m3u8")
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", concat_mp3,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    index_m3u8
                ], check=True)
                print(f"[worker] HLS gerado em: {index_m3u8}")

                # Marca como "processado", para não repetir
                processed.add(filename)

            except Exception as e:
                # Em caso de qualquer erro, ainda marca como processado para não travar
                print(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        # Espera 1 segundo antes de checar novamente
        time.sleep(1)
