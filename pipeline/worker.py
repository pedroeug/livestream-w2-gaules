# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
from elevenlabs import generate, set_api_key
import subprocess

def worker_loop(audio_dir: str, lang: str):
    model = whisper.load_model("base")
    set_api_key(os.getenv("ELEVENLABS_API_KEY"))

    processed = set()

    while True:
        # Lista todos os WAVs novos
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            print(f"[worker] Encontrou novo segmento: {wav_path}")

            # 1) Transcrição
            print(f"[worker] Transcrevendo {wav_path} ...")
            result = model.transcribe(wav_path)
            text = result["text"]
            print(f"[worker] Transcrição: {text}")

            # 2) Tradução (usar Deepl)
            print(f"[worker] Traduzindo para {lang} ...")
            translator = DeeplTranslator(source="auto", target=lang)
            translated = translator.translate(text)
            print(f"[worker] Tradução: {translated}")

            # 3) Síntese ElevenLabs
            print(f"[worker] Síntese ElevenLabs para texto traduzido ...")
            audio = generate(text=translated, voice="Rachel", model="eleven_multilingual_v1")
            output_wav = wav_path.replace(".wav", f"_{lang}.wav")
            with open(output_wav, "wb") as f:
                f.write(audio)
            print(f"[worker] Áudio sintetizado salvo em {output_wav}")

            # 4) Empacotar em HLS (exemplo simplificado):
            channel = os.path.basename(audio_dir)
            hls_dir = os.path.join("hls", channel, lang)
            os.makedirs(hls_dir, exist_ok=True)
            ts_filename = filename.replace(".wav", f"_{lang}.ts")
            hls_path = os.path.join(hls_dir, ts_filename)
            print(f"[worker] Convertendo para TS: {hls_path}")
            ffmpeg_cmd = (
                f'ffmpeg -y -i {output_wav} -c:a aac -b:a 128k '
                f'-hls_time 10 -hls_playlist_type event '
                f'-hls_segment_filename "{hls_dir}/%03d.ts" '
                f'{hls_dir}/index.m3u8'
            )
            subprocess.run(ffmpeg_cmd, shell=True)
            print(f"[worker] HLS gerado em {hls_dir}/index.m3u8")

            processed.add(filename)

        time.sleep(1)  # espera antes de checar novamente
