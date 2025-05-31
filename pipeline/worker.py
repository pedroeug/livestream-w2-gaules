# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import requests
import subprocess

def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Síntese de voz (ElevenLabs via REST).
      5. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # Carrega o modelo Whisper
    model = whisper.load_model("base")

    # Captura credenciais do ElevenLabs via variáveis de ambiente
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    eleven_voice_id = os.getenv("ELEVENLABS_VOICE_ID")  # Ex: "pNInz6obpgDQGcFmaJgB"
    if not elevenlabs_api_key or not eleven_voice_id:
        print("[worker] AVISO: ELEVENLABS_API_KEY ou ELEVENLABS_VOICE_ID não definido. TTS será pulado.")

    processed = set()

    while True:
        # Lista todos os arquivos .wav ainda não processados
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            print(f"[worker] Encontrou novo segmento: {wav_path}")

            try:
                # 1) Transcrição com Whisper
                print(f"[worker] Transcrevendo {wav_path} ...")
                result = model.transcribe(wav_path)
                text = result["text"].strip()
                print(f"[worker] Transcrição: {text}")

                # 2) Tradução com DeepL
                print(f"[worker] Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                print(f"[worker] Tradução: {translated}")

                # 3) Síntese de voz com ElevenLabs (via HTTP)
                if elevenlabs_api_key and eleven_voice_id:
                    print(f"[worker] Sintetizando texto traduzido com ElevenLabs ...")
                    tts_endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{eleven_voice_id}"
                    headers = {
                        "xi-api-key": elevenlabs_api_key,
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "text": translated,
                        "voice_settings": {
                            "stability": 0.75,
                            "similarity_boost": 0.75
                        }
                    }
                    response = requests.post(tts_endpoint, json=payload, headers=headers)
                    if response.status_code == 200:
                        output_wav = wav_path.replace(".wav", f"_{lang}.wav")
                        with open(output_wav, "wb") as f:
                            f.write(response.content)
                        print(f"[worker] Áudio sintetizado salvo em {output_wav}")
                    else:
                        print(f"[worker] Erro ElevenLabs ({response.status_code}): {response.text}")
                        processed.add(filename)
                        continue
                else:
                    print("[worker] Pulando síntese ElevenLabs: credenciais não configuradas.")
                    processed.add(filename)
                    continue

                # 4) Empacotar em HLS via ffmpeg
                channel = os.path.basename(audio_dir)
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                print(f"[worker] Convertendo {output_wav} para HLS em {output_index} ...")
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", output_wav,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    output_index
                ]
                subprocess.run(ffmpeg_cmd, check=True)
                print(f"[worker] HLS gerado em {output_index}")

                processed.add(filename)

            except Exception as e:
                print(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)  # Espera 1 segundo antes de checar novamente
